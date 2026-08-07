from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    avatar_id: str | None = None
    avatar_photo: str | None = None
    identity_hue: int | None = None
    changelog_opt_out: bool = False
    # Features sin terminar visibles para este usuario. El frontend las usa solo
    # para enseñar u ocultar; la puerta de verdad está en el backend (deps.py).
    feature_flags: list[str] = []

    @field_validator("feature_flags", mode="before")
    @classmethod
    def _none_is_empty(cls, v: object) -> object:
        # En la BD la columna es nullable (null = ninguna, y así las filas
        # antiguas no necesitan backfill). Fuera siempre es una lista, para que
        # el frontend no tenga que distinguir null de [].
        return [] if v is None else v

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
