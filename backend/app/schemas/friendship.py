from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.friendship import FriendshipKind, FriendshipStatus


class UserMinimal(BaseModel):
    id: int
    name: str
    email: str
    avatar_id: str | None = None
    avatar_photo: str | None = None
    identity_hue: int | None = None

    class Config:
        from_attributes = True


class FriendshipOut(BaseModel):
    id: int
    requester: UserMinimal
    receiver: UserMinimal
    status: FriendshipStatus
    kind: FriendshipKind
    partner_proposed_by: int | None = None
    can_add_food: bool
    can_add_food_requester: bool
    shared_inventory_requester: bool
    shared_inventory_receiver: bool
    shared_inventory: bool  # computed: both true
    duel_opt_in_requester: bool
    duel_opt_in_receiver: bool
    duel_active: bool  # computed: both true
    created_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def _photos_only_between_accepted(self) -> "FriendshipOut":
        """La foto solo se ve cuando la relación está aceptada.

        Aquí y no en cada endpoint a propósito: una solicitud pendiente la puede
        mandar cualquiera que tenga tu código, y hasta que dices que sí no vas a
        ver una imagen que ha elegido un desconocido. El avatar predefinido sí
        se enseña — son 18 dibujos nuestros, no puede haber sorpresa.
        """
        if self.status is not FriendshipStatus.accepted:
            self.requester.avatar_photo = None
            self.receiver.avatar_photo = None
        return self


class FriendshipRequest(BaseModel):
    """Send a friend request, by invite code or (legacy) by email.

    `code` es el camino nuevo: enseñar un código es mejor UX que pedir el email y
    evita que baste con conocer tu dirección para dejarte una solicitud delante.
    `email` sigue aceptado porque los APK ya instalados solo saben mandar eso;
    en cuanto no queden clientes viejos se puede quitar.
    """
    email: str | None = None
    code: str | None = None
    kind: Literal["friend", "partner"] = "friend"

    @model_validator(mode="after")
    def _exactly_one(self) -> "FriendshipRequest":
        if bool(self.email) == bool(self.code):
            raise ValueError("Indica un código de invitación o un email, no ambos")
        return self


class FriendshipReport(BaseModel):
    """Denunciar a la otra persona de una relación (y bloquearla).

    Van juntos a propósito: quien denuncia no quiere seguir viendo a esa persona
    mientras alguien revisa la denuncia.
    """
    reason: str = Field(default="", max_length=500)


class FriendshipUpdate(BaseModel):
    """Accept/reject a request, or update permissions.

    `kind` does double duty on an accepted friendship: asking for "partner"
    proposes it (and seals it once the other side asks too), asking for "friend"
    steps back down. On a pending request it can only lower what was proposed.
    """
    status: Literal["accepted", "rejected"] | None = None
    kind: Literal["friend", "partner"] | None = None
    can_add_food: bool | None = None           # receiver controls
    can_add_food_requester: bool | None = None  # requester controls
    # Each side opts in independently
    shared_inventory_requester: bool | None = None
    shared_inventory_receiver: bool | None = None
    duel_opt_in_requester: bool | None = None
    duel_opt_in_receiver: bool | None = None
