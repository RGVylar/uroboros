from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pot(Base):
    """Una olla: algo que se cocina una vez y se come en varios días, a
    menudo entre los dos de la pareja. Se apunta por raciones o, si alguien
    la pesó ya cocinada, por gramos.

    No guarda cuánto queda: lo comido sale de las entradas del diario que
    llevan su `pot_id`. Así borrar una entrada devuelve su parte a la olla sin
    nada más que hacer.
    """

    __tablename__ = "pots"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # La pareja con la que se comparte, fijada al crearla. Nula = solo del dueño.
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Para cuántas raciones da, más o menos. Una ración = 1/servings de la olla.
    servings: Mapped[float] = mapped_column(Float, nullable=False)
    # Peso de la comida ya cocinada (sin el recipiente). Opcional: solo con él
    # se puede apuntar en gramos. Nunca se deduce de los ingredientes en crudo,
    # que no pesan lo mismo (la pasta cocida pesa el doble).
    cooked_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ingredients: Mapped[list["PotIngredient"]] = relationship(
        back_populates="pot", cascade="all, delete-orphan"
    )

    @property
    def raw_weight(self) -> float:
        return sum(i.grams for i in self.ingredients)


class PotIngredient(Base):
    """Lo que se echó a la olla, en crudo. Copia congelada: si la olla salió
    de una receta y luego se edita la receta, esta olla no cambia."""

    __tablename__ = "pot_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    pot_id: Mapped[int] = mapped_column(
        ForeignKey("pots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    grams: Mapped[float] = mapped_column(Float, nullable=False)

    pot: Mapped[Pot] = relationship(back_populates="ingredients")
    product: Mapped["Product"] = relationship(lazy="joined")  # noqa: F821
