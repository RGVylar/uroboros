"""Informes de problemas: la captura opcional y el contexto que se adjunta."""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

# Una captura de móvil a pantalla completa ronda 1-3 MB en PNG.
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
# Telegram la reescala igualmente; más grande solo gasta subida.
MAX_SIDE_PX = 1600

Image.MAX_IMAGE_PIXELS = 40_000_000


class InvalidScreenshot(Exception):
    pass


def screenshot_to_jpeg(raw: bytes) -> bytes:
    """Bytes subidos → JPEG limpio para reenviar.

    Se re-codifica siempre, aunque ya sea un JPEG: así se cae el EXIF (con la
    ubicación, si la hay) y lo que sale hacia Telegram es una imagen que hemos
    generado nosotros, no el fichero que mandó el cliente.
    """
    try:
        with Image.open(BytesIO(raw)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX), Image.LANCZOS)
            buf = BytesIO()
            im.save(buf, "JPEG", quality=82)
            return buf.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise InvalidScreenshot(str(exc)) from exc


def device_from_user_agent(ua: str) -> str:
    """El trozo del User-Agent que dice qué móvil es, sin el resto del ruido.

    `Mozilla/5.0 (Linux; Android 14; 23028RA60L Build/UKQ1...) AppleWebKit...`
    → `Linux; Android 14; 23028RA60L Build/UKQ1...`. Si no hay paréntesis, el
    UA entero recortado: mejor algo que nada.
    """
    start, end = ua.find("("), ua.find(")")
    if 0 <= start < end:
        return ua[start + 1 : end][:255]
    return ua[:255]
