from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://uroboros:uroboros@localhost:5432/uroboros"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 90  # 90 días
    off_base_url: str = "https://es.openfoodfacts.org"
    demo_mode: bool = False
    resend_api_key: str = ""
    email_from: str = "uroboros <noreply@comida.mugrelore.com>"
    app_url: str = "https://comida.mugrelore.com"


settings = Settings()
