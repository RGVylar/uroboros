import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.limiter import limiter
from app.models import User
from app.models.password_reset import PasswordResetToken
from app.schemas.auth import TokenResponse, UserLogin, UserOut, UserRegister
from app.security import create_access_token, hash_password, verify_password
from app.services.telegram_alerts import send_new_user_alert

router = APIRouter(prefix="/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        subscription_status="trial",
        trial_started_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    await send_new_user_alert(user.name, user.email, user_count)
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/15minutes")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("2/10minutes")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> None:
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    # Siempre responder 204 para no revelar si el email existe
    if not user:
        return

    # Invalidar tokens anteriores
    old_tokens = list(db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used.is_(False),
        )
    ))
    for t in old_tokens:
        t.used = True

    token_value = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token_value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    db.add(reset_token)
    db.commit()

    reset_url = f"{settings.app_url}/reset-password?token={token_value}"

    if settings.resend_api_key:
        try:
            import resend
            resend.api_key = settings.resend_api_key
            resend.Emails.send({
                "from": settings.email_from,
                "to": user.email,
                "subject": "Recupera tu contraseña — uroboros",
                "html": f"""
                <div style="font-family:sans-serif; max-width:480px; margin:0 auto; padding:2rem;">
                    <h1 style="font-size:1.5rem; color:#111;">Recuperar contraseña</h1>
                    <p>Hola {user.name},</p>
                    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en uroboros.</p>
                    <p>Haz clic en el botón para crear una nueva contraseña. El enlace expira en <strong>2 horas</strong>.</p>
                    <a href="{reset_url}"
                       style="display:inline-block; margin:1.5rem 0; padding:0.875rem 1.5rem;
                              background:#22c55e; color:#fff; text-decoration:none;
                              border-radius:10px; font-weight:700;">
                        Restablecer contraseña
                    </a>
                    <p style="color:#666; font-size:0.875rem;">
                        Si no solicitaste esto, ignora este email. Tu contraseña no cambiará.
                    </p>
                    <p style="color:#aaa; font-size:0.75rem;">uroboros · Come mejor. Juntos.</p>
                </div>
                """,
            })
        except Exception:
            pass  # No revelar fallos de email al cliente


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    if len(payload.new_password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La contraseña debe tener al menos 8 caracteres")

    reset_token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token == payload.token)
    )
    if not reset_token or reset_token.used:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enlace inválido o ya utilizado")
    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace ha expirado. Solicita uno nuevo")

    user = db.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    user.password_hash = hash_password(payload.new_password)
    reset_token.used = True
    db.commit()
