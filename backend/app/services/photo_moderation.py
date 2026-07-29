"""Rechazar una foto de perfil desde el chat de admin.

Cierra el bucle de moderación: la alerta enseña la foto, y el botón la retira sin
tener que entrar en la base de datos. La persona se entera por notificación, no
descubriéndolo por casualidad al mirar su perfil.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.services.avatar_photo_service import delete_photo

# El scheduler ya sabe mandar a todas las suscripciones de un usuario y limpiar
# las caducadas. Es privado, pero duplicar aquí ese manejo sería peor que
# importarlo.
from app.services.notification_scheduler import _send_to_user

REJECTED_TITLE = "Tu foto de perfil"
REJECTED_BODY = (
    "La hemos retirado porque no cumple las normas de la comunidad. "
    "Puedes subir otra o elegir uno de los avatares."
)


class RejectionResult:
    """Qué pasó, para poder contárselo a quien pulsó el botón."""

    def __init__(self, ok: bool, message: str, user_name: str = "") -> None:
        self.ok = ok
        self.message = message
        self.user_name = user_name


def reject_photo(db: Session, user_id: int, photo_name: str) -> RejectionResult:
    """Borra la foto de un usuario y se lo notifica.

    `photo_name` tiene que coincidir con la que tiene puesta ahora mismo. Si no
    coincide es que la cambió después de que saltara la alerta, y rechazar la
    vieja no puede llevarse por delante una que nadie ha revisado.
    """
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        return RejectionResult(False, "Ese usuario ya no existe")
    if not user.avatar_photo:
        return RejectionResult(False, "Ya no tiene foto", user.name)
    if user.avatar_photo != photo_name:
        return RejectionResult(False, "Ha cambiado la foto desde el aviso", user.name)

    user.avatar_photo = None
    db.commit()
    delete_photo(photo_name)

    # Que falle el aviso no deshace el borrado: lo importante era retirarla.
    try:
        _send_to_user(db, user_id, title=REJECTED_TITLE, body=REJECTED_BODY, url="/profile")
    except Exception:
        pass

    return RejectionResult(True, "Foto retirada y usuario avisado", user.name)
