"""Fotos de perfil: validar, reencodear y guardar.

La regla que sostiene todo lo demás: **nunca se guarda ni se sirve el fichero que
sube el usuario**. Se abre, se reencodea a WebP y lo que llega a disco es una
imagen nueva generada por nosotros. Eso, de una sola vez:

- borra el EXIF, y con él las coordenadas GPS que trae cualquier foto de móvil;
- descarta un SVG con <script> dentro (Pillow ni siquiera lo abre) y los
  polyglots que se hacen pasar por imagen;
- deja un único formato y tamaño, así que el frontend no tiene que adivinar.
"""
import tempfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

# 4 MB. Una foto de perfil no necesita más y el límite se comprueba antes de
# leer el cuerpo entero. El tope de verdad va en Caddy (request_body max_size):
# esto es la segunda línea, no la primera.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024

SIZE_PX = 256
WEBP_QUALITY = 82

# Una imagen de 40 MP ya es absurda para un avatar; por encima de eso lo que
# tienes es una bomba de descompresión, no una foto. Pillow avisa a partir de su
# propio umbral, pero el nuestro es el que decide.
Image.MAX_IMAGE_PIXELS = 40_000_000


class InvalidImage(Exception):
    """Lo subido no es una imagen que podamos procesar."""


def media_root() -> Path:
    """Directorio de fotos, creado si hace falta.

    Sin MEDIA_DIR configurado cae en un temporal: sirve para desarrollo y para
    los tests, y en producción se nota enseguida si alguien olvidó el .env.
    """
    root = Path(settings.media_dir) if settings.media_dir else Path(tempfile.gettempdir()) / "uroboros-media"
    avatars = root / "avatars"
    avatars.mkdir(parents=True, exist_ok=True)
    return avatars


def _square(im: Image.Image) -> Image.Image:
    """Recorte centrado al cuadrado. Se pinta en círculo: el centro es la cara."""
    w, h = im.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    return im.crop((left, top, left + side, top + side))


def process_and_store(raw: bytes) -> str:
    """Bytes subidos → nombre del WebP guardado. Lanza InvalidImage si no cuela."""
    try:
        with Image.open(BytesIO(raw)) as im:
            # exif_transpose antes de nada: es el único momento en que el EXIF
            # nos importa (la orientación). Después se tira entero.
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            im = _square(im).resize((SIZE_PX, SIZE_PX), Image.LANCZOS)

            name = f"{uuid4().hex}.webp"
            # Nombre aleatorio, no derivado del user_id: si se filtra una URL no
            # se pueden deducir las demás.
            im.save(media_root() / name, "WEBP", quality=WEBP_QUALITY, method=6)
            return name
    except (
        UnidentifiedImageError,
        # DecompressionBombError hereda de Exception, no de ValueError: si no se
        # nombra aquí, la bomba sale como un 500 en vez de como un rechazo.
        Image.DecompressionBombError,
        OSError,
        ValueError,
    ) as exc:
        raise InvalidImage(str(exc)) from exc


def read_thumbnail_jpeg(name: str) -> bytes | None:
    """El WebP guardado, como JPEG, para mandarlo por Telegram.

    En JPEG y no en WebP porque sendPhoto trata el WebP de forma irregular (a
    veces lo interpreta como sticker). Releer un fichero de 20 KB no le duele a
    nadie y evita arrastrar los bytes por medio código.
    """
    try:
        with Image.open(media_root() / name) as im:
            buf = BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=80)
            return buf.getvalue()
    except (OSError, ValueError):
        return None


def delete_photo(name: str | None) -> None:
    """Borra el fichero si existe. Silencioso a propósito.

    Se llama al cambiar de foto y al borrar la cuenta. Que falte el fichero no
    puede impedir ninguna de las dos cosas: el estado que manda es la fila.
    """
    if not name:
        return
    try:
        (media_root() / name).unlink(missing_ok=True)
    except OSError:
        pass
