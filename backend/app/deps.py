from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    sub = decode_token(token)
    if sub is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = db.get(User, int(sub))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_premium(user: User = Depends(get_current_user)) -> User:
    """Dependency that blocks access for free-tier users."""
    if not user.is_premium_or_trial:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="premium_required",
        )
    return user


def require_feature_flag(flag: str):
    """Puerta para features aún no publicadas (`User.feature_flags`).

    Esconder el botón en el frontend no es control de acceso: el endpoint sigue
    ahí y cualquiera con una cuenta puede llamarlo. Para una feature a medias eso
    no es solo falta de higiene — un endpoint caro (OCR, por ejemplo) sin puerta
    es CPU gratis para quien se registre.

    Responde **404 y no 403** a propósito: una feature que todavía no existe para
    ti no debería ni asomar que existe.
    """

    def _dep(user: User = Depends(get_current_user)) -> User:
        if not user.has_flag(flag):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
        return user

    return _dep
