"""Escaneo de tickets de compra. Detrás del flag `receipt_scan` (§9 del plan).

De momento devuelve el OCR en crudo: texto y palabras con su caja. El parser que
convierte eso en artículos viene después, y vive también aquí en el backend a
propósito — es la parte frágil (cada cadena maqueta distinto) y así se arregla
con un deploy en vez de con una release de la APK.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.deps import require_feature_flag
from app.limiter import limiter
from app.models import User
from app.services.receipt_ocr import (
    MAX_UPLOAD_BYTES,
    InvalidImage,
    OcrUnavailable,
    extract,
)

FLAG = "receipt_scan"

router = APIRouter(prefix="/receipts", tags=["receipts"])


class WordOut(BaseModel):
    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float


class ScanOut(BaseModel):
    """OCR en crudo. Las coordenadas van en píxeles de la imagen ya procesada,
    no de la que subió el usuario, así que `image_width/height` son la referencia
    para interpretarlas."""

    text: str
    words: list[WordOut]
    image_width: int
    image_height: int


@router.post("/scan", response_model=ScanOut)
@limiter.limit("20/hour")
async def scan_receipt(
    request: Request,
    file: UploadFile = File(...),
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

    return ScanOut(
        text=result.text,
        words=[WordOut(**w.__dict__) for w in result.words],
        image_width=result.image_width,
        image_height=result.image_height,
    )
