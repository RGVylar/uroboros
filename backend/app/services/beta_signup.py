"""Cola de quien se apunta a la prueba cerrada desde /beta."""
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BetaSignup

# Lo justo para descartar lo que claramente no es un email (falta la @, el
# dominio no tiene punto). La prueba de verdad es que Play Console lo acepte.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: str) -> str | None:
    email = raw.strip().lower()
    if len(email) > 255 or not _EMAIL_RE.match(email):
        return None
    return email


def register(db: Session, email: str, name: str, lang: str) -> bool:
    """Apunta a alguien. Devuelve False si ya estaba (y no toca su fila).

    Quien se apunta dos veces suele ser alguien que no se acuerda de si lo
    hizo: la respuesta es la misma, y así la página tampoco sirve para
    averiguar si un email concreto está en la lista.
    """
    exists = db.scalar(select(BetaSignup.id).where(BetaSignup.email == email))
    if exists is not None:
        return False
    db.add(BetaSignup(email=email, name=name.strip()[:80], lang=lang))
    db.commit()
    return True


def pending_count(db: Session) -> int:
    """Cuántos faltan por meter en la lista de Play Console."""
    return db.scalar(select(func.count()).select_from(BetaSignup).where(BetaSignup.added.is_(False))) or 0
