"""OCR de tickets de compra: de una foto a texto con coordenadas.

Dos reglas que sostienen el resto:

**La foto del usuario nunca toca el disco.** Se abre en memoria, se reencodea, y
lo único que llega a un fichero temporal es una imagen nuestra ya procesada, que
se borra al salir. Igual que en `avatar_photo_service`, y por los mismos motivos:
mata el EXIF (con el GPS dentro), descarta polyglots y SVG con script, y deja un
único formato. Un ticket además lleva comercio, fecha, hora y a veces los últimos
dígitos de la tarjeta — razón de sobra para no guardarlo.

**Lo que se devuelve son palabras con su caja, no un texto plano.** Leer un
ticket es un problema de maquetación: la descripción va a la izquierda y el
importe alineado a la derecha, a la misma altura. Con las coordenadas eso se
reconstruye; con una cadena de texto se adivina. El parser que viene después
depende de esto.

El preprocesado (normalizar tamaño → gris → Otsu) y el `--psm 4` salen de medir
8 tickets reales con `backend/scripts/receipt_spike.py`. Ese script sigue siendo
la herramienta para revisar estas constantes cuando haya tickets nuevos; aquí
solo se aplica la combinación ganadora.
"""
from __future__ import annotations

import csv
import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

# 8 MB. Una foto de ticket a resolución completa de móvil cabe de sobra; el tope
# de verdad va en Caddy (request_body max_size), esto es la segunda línea.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# Por encima de esto no tienes una foto, tienes una bomba de descompresión.
Image.MAX_IMAGE_PIXELS = 40_000_000

# Ancho al que se normaliza antes de umbralizar.
#
# El spike midió que gana escalar ×2, pero ×2 sobre una foto de iPhone (~4000 px)
# daría 8000 px: lento y sin ganancia, porque el detalle ya está ahí. Fijar un
# ancho objetivo quita la resolución de la ecuación — sube las fotos pequeñas y
# baja las enormes, y el OCR ve siempre letras del mismo tamaño.
#
# OJO: 2000 es una extrapolación. Las muestras del spike venían comprimidas de
# chat (316–1080 px), así que este número está por confirmar con fotos reales a
# resolución completa. Revisar con el spike cuando las haya.
TARGET_WIDTH = 2000

# Un ticket es una columna de texto con tamaños variables. psm 6 (bloque
# uniforme) puntuó peor en 7 de los 8 tickets medidos.
PSM = "4"

# Tesseract puede atascarse con una imagen rara, y esto corre dentro de una
# petición HTTP.
TIMEOUT_S = 60


class InvalidImage(Exception):
    """Lo subido no es una imagen que podamos procesar."""


class OcrUnavailable(Exception):
    """Falta el binario de Tesseract. Es un fallo de despliegue, no del usuario."""


@dataclass(frozen=True)
class Word:
    """Una palabra y dónde estaba, en píxeles de la imagen ya procesada."""

    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float


@dataclass(frozen=True)
class OcrResult:
    text: str
    words: list[Word]
    image_width: int
    image_height: int


def _otsu_threshold(gray: Image.Image) -> int:
    """Umbral de Otsu a partir del histograma.

    El papel térmico se decolora de forma desigual, así que un umbral fijo borra
    media mitad del ticket. Otsu lo calcula por imagen.
    """
    hist = gray.histogram()[:256]
    total = sum(hist)
    if total == 0:
        return 128
    sum_all = sum(i * h for i, h in enumerate(hist))
    sum_bg = 0.0
    weight_bg = 0
    best_var, best_t = -1.0, 128
    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        var = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var > best_var:
            best_var, best_t = var, t
    return best_t


def preprocess(raw: bytes) -> Image.Image:
    """Bytes subidos → imagen en blanco y negro lista para Tesseract.

    Aquí es donde el fichero del usuario deja de existir: lo que sale es una
    imagen nueva generada por nosotros, sin EXIF ni nada de lo que trajera.
    """
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise InvalidImage(str(e)) from e

    img = ImageOps.exif_transpose(img)  # la foto del móvil viene rotada
    gray = ImageOps.autocontrast(img.convert("L"))

    if gray.width != TARGET_WIDTH:
        ratio = TARGET_WIDTH / gray.width
        gray = gray.resize(
            (TARGET_WIDTH, max(1, round(gray.height * ratio))), Image.LANCZOS
        )

    t = _otsu_threshold(gray)
    return gray.point(lambda p, t=t: 255 if p > t else 0, mode="1")


def _tesseract_cmd() -> str:
    exe = shutil.which(settings.tesseract_cmd) or (
        settings.tesseract_cmd if Path(settings.tesseract_cmd).is_file() else None
    )
    if exe is None:
        raise OcrUnavailable(
            f"No encuentro el binario de Tesseract ({settings.tesseract_cmd!r}). "
            "Instálalo con: apt install tesseract-ocr tesseract-ocr-spa"
        )
    return exe


def _parse_tsv(tsv: str) -> list[Word]:
    """TSV de Tesseract → palabras con caja, descartando las filas de estructura.

    El TSV trae una fila por nivel (página, bloque, párrafo, línea, palabra). Solo
    las de nivel 5 llevan texto; el resto son contenedores con `conf` a -1.
    """
    words: list[Word] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            conf = float(row["conf"])
            if conf < 0:
                continue
            words.append(
                Word(
                    text=text,
                    left=int(row["left"]),
                    top=int(row["top"]),
                    width=int(row["width"]),
                    height=int(row["height"]),
                    conf=conf,
                )
            )
        except (KeyError, ValueError):
            continue  # fila malformada: una palabra menos, no un 500
    return words


def extract(raw: bytes) -> OcrResult:
    """Foto de un ticket → texto y palabras con coordenadas.

    Lanza `InvalidImage` si no se puede abrir y `OcrUnavailable` si falta el
    binario.
    """
    img = preprocess(raw)
    exe = _tesseract_cmd()

    with tempfile.TemporaryDirectory(prefix="uroboros-ocr-") as tmp:
        src = Path(tmp) / "in.png"
        img.save(src)
        out_base = Path(tmp) / "out"

        base_cmd = [exe, str(src), str(out_base), "-l", settings.tesseract_lang, "--psm", PSM]
        if settings.tesseract_tessdata:
            base_cmd += ["--tessdata-dir", settings.tesseract_tessdata]

        results: dict[str, str] = {}
        for fmt in ("txt", "tsv"):
            try:
                subprocess.run(
                    base_cmd + [fmt], capture_output=True, check=False, timeout=TIMEOUT_S
                )
            except subprocess.TimeoutExpired as e:
                raise OcrUnavailable("El OCR ha tardado demasiado") from e
            produced = out_base.with_suffix(f".{fmt}")
            if fmt == "tsv" and not produced.exists():
                # `txt` y `tsv` son ficheros de configuración que Tesseract busca
                # en <tessdata>/configs. Si falta, se queda sin escribir el TSV y
                # devuelve solo texto — sin coordenadas, y **sin error**. Callarlo
                # aquí sería devolver un 200 inútil que rompe el parser mucho más
                # tarde y sin pista de por qué. Pasa al apuntar --tessdata-dir a
                # una carpeta con los idiomas pero sin `configs` al lado.
                raise OcrUnavailable(
                    "Tesseract no ha generado el TSV: falta el fichero de configuración "
                    "'tsv'. Comprueba que exista <tessdata>/configs/tsv en la ruta de "
                    "TESSERACT_TESSDATA."
                )
            results[fmt] = (
                produced.read_text(encoding="utf-8", errors="replace")
                if produced.exists()
                else ""
            )

    return OcrResult(
        text=results["txt"],
        words=_parse_tsv(results["tsv"]),
        image_width=img.width,
        image_height=img.height,
    )
