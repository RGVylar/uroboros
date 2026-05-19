from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_JWT_DEFAULTS = {
    "change-me-in-production",
    "secret",
    "changeme",
    "your-secret-key",
    "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://uroboros:uroboros@localhost:5432/uroboros"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_secure(cls, v: str) -> str:
        if v in _INSECURE_JWT_DEFAULTS or len(v) < 32:
            raise ValueError(
                "JWT_SECRET is insecure or too short (min 32 chars). "
                "Set a secure value with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v
    jwt_expire_minutes: int = 60 * 24 * 90  # 90 días
    off_base_url: str = "https://es.openfoodfacts.org"
    demo_mode: bool = False
    resend_api_key: str = ""
    email_from: str = "uroboros <noreply@mugrelore.com>"
    app_url: str = "https://comida.mugrelore.com"
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_email: str = "mailto:admin@uroboros.app"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
