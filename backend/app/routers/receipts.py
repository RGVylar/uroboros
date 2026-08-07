"""Escaneo de tickets de compra. Detrás del flag `receipt_scan` (§9 del plan).

De momento devuelve el OCR en crudo: texto y palabras con su caja. El parser que
convierte eso en artículos viene después, y vive también aquí en el backend a
propósito — es la parte frágil (cada cadena maqueta distinto) y así se arregla
con un deploy en vez de con una release de la APK.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_feature_flag
from app.limiter import limiter
from app.models import ANY_STORE, User
from app.models.inventory import INVENTORY_LOCATIONS, INVENTORY_UNITS
from app.services.receipt_apply import ACTIONS, LineToApply, apply_receipt, undo_receipt
from app.services.receipt_matcher import match_line
from app.services.receipt_ocr import (
    MAX_UPLOAD_BYTES,
    InvalidImage,
    OcrUnavailable,
    extract,
)
from app.services.receipt_parser import parse

FLAG = "receipt_scan"

router = APIRouter(prefix="/receipts", tags=["receipts"])


class WordOut(BaseModel):
    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float


class SuggestionOut(BaseModel):
    product_id: int
    product_name: str
    score: float
    # 'alias' | 'usados' | 'catalogo'. La revisión lo usa para saber qué da por
    # bueno: un alias es una decisión que ya tomó el usuario, el parecido es una
    # opinión nuestra.
    source: str
    confident: bool


class ScannedLineOut(BaseModel):
    raw: str
    quantity: float
    unit: str
    amount: float | None
    unit_price: float | None
    suggestion: SuggestionOut | None
    # False solo cuando la aritmética del propio ticket NO cuadra; None si
    # faltaban datos para comprobarlo, que no es lo mismo que estar mal.
    arithmetic_ok: bool | None
    # El usuario marcó esta línea como "no es comida" en una compra anterior.
    ignored: bool


class ScanOut(BaseModel):
    """OCR en crudo **más** las líneas ya interpretadas.

    Se devuelve también el texto y las palabras porque el parser todavía es
    joven: cuando se le escape una línea, la crudeza es lo que permite ver por
    qué. Las coordenadas van en píxeles de la imagen ya procesada, no de la que
    subió el usuario.
    """

    text: str
    words: list[WordOut]
    image_width: int
    image_height: int
    lines: list[ScannedLineOut]


class ApplyLineIn(BaseModel):
    raw: str
    action: str = "add"
    product_id: int | None = None
    quantity: float = Field(default=1.0, gt=0)
    unit: str = "unit"
    location: str = "pantry"
    price_per_100g: float | None = None


class ApplyIn(BaseModel):
    store: str = ANY_STORE
    purchased_at: datetime | None = None
    lines: list[ApplyLineIn]


class ApplyOut(BaseModel):
    import_id: int
    applied: int


@router.post("/scan", response_model=ScanOut)
@limiter.limit("20/hour")
async def scan_receipt(
    request: Request,
    file: UploadFile = File(...),
    store: str = Form(default=ANY_STORE),
    db: Session = Depends(get_db),
    user: User = Depends(require_feature_flag(FLAG)),
) -> ScanOut:
    """Foto de un ticket → texto con coordenadas. La imagen no se guarda.

    El límite por hora no es por abuso de terceros —el flag ya cierra la puerta—
    sino porque el OCR es lo más caro que corre en esta máquina y una pantalla
    con un bucle podría tumbarla sola.
    """
    # Content-Length primero: rechaza lo grande sin haberlo leído. No es fiable
    # por sí solo (se puede mentir u omitir), por eso el read() también tiene tope.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La foto pesa demasiado")

    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La foto pesa demasiado")
    if not raw:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No has enviado ninguna foto")

    try:
        result = extract(raw)
    except InvalidImage:
        # Decide Pillow, no el content-type ni la extensión.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No hemos podido leer esa imagen")
    except OcrUnavailable as e:
        # Falta el binario o ha tardado demasiado: es cosa nuestra, no suya.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))

    lines = []
    for item in parse(result.words):
        m = match_line(db, user, item.raw, store)
        lines.append(
            ScannedLineOut(
                raw=item.raw,
                quantity=item.quantity,
                unit=item.unit,
                amount=item.amount,
                unit_price=item.unit_price,
                arithmetic_ok=item.arithmetic_ok,
                ignored=m.source == "ignorar",
                suggestion=(
                    SuggestionOut(
                        product_id=m.product.id,
                        product_name=m.product.name,
                        score=round(m.score, 2),
                        source=m.source,
                        confident=m.is_confident,
                    )
                    if m.product is not None
                    else None
                ),
            )
        )

    return ScanOut(
        text=result.text,
        words=[WordOut(**w.__dict__) for w in result.words],
        image_width=result.image_width,
        image_height=result.image_height,
        lines=lines,
    )


@router.post("/apply", response_model=ApplyOut, status_code=status.HTTP_201_CREATED)
def apply_scanned_receipt(
    payload: ApplyIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature_flag(FLAG)),
) -> ApplyOut:
    """Vuelca a la despensa las líneas ya confirmadas por el usuario.

    Aquí no se adivina nada: lo que llega lo ha revisado una persona. Se valida
    de todas formas porque el cliente no es de fiar aunque sea el nuestro.
    """
    for line in payload.lines:
        if line.action not in ACTIONS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Acción desconocida: {line.action}")
        if line.unit not in INVENTORY_UNITS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unidad desconocida: {line.unit}")
        if line.location not in INVENTORY_LOCATIONS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Sitio desconocido: {line.location}")
        if line.action == "add" and line.product_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Falta el producto de una línea")

    tanda = apply_receipt(
        db,
        user,
        store=payload.store,
        purchased_at=payload.purchased_at,
        lines=[
            LineToApply(
                raw=l.raw,
                action=l.action,
                product_id=l.product_id,
                quantity=l.quantity,
                unit=l.unit,
                location=l.location,
                price_per_100g=l.price_per_100g,
            )
            for l in payload.lines
        ],
    )
    return ApplyOut(import_id=tanda.id, applied=tanda.line_count)


@router.delete("/imports/{import_id}", status_code=status.HTTP_204_NO_CONTENT)
def undo_import(
    import_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature_flag(FLAG)),
) -> None:
    """Deshace una importación entera.

    Resta lo que sumó en vez de poner a cero: entre importar y deshacer el
    usuario ha podido comerse parte de lo que compró.
    """
    if not undo_receipt(db, user, import_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa importación no existe")
