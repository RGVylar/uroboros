"""Alta y resolución de códigos de invitación."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.invite_codes import generate_code, normalize
from app.models import User

# Colisionar es improbabilísimo (32⁸), pero el índice es único y una colisión sin
# reintento sería un 500 en la cara del usuario. Barato de cubrir.
_MAX_ATTEMPTS = 5


def ensure_invite_code(db: Session, user: User) -> str:
    """El código del usuario, generándolo y persistiéndolo si no tenía."""
    if user.invite_code:
        return user.invite_code

    for _ in range(_MAX_ATTEMPTS):
        user.invite_code = generate_code()
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(user)
        return user.invite_code

    raise RuntimeError("No se pudo generar un código de invitación único")


def resolve_code(db: Session, raw: str) -> User | None:
    """Usuario dueño del código tecleado, o None si no vale o no existe.

    Devuelve None en ambos casos a propósito: quien llama responde lo mismo para
    un código mal escrito que para uno que no existe, y así el endpoint no
    confirma qué códigos están cogidos.
    """
    code = normalize(raw)
    if not code:
        return None
    return db.scalar(select(User).where(User.invite_code == code))
