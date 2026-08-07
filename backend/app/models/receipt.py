from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Qué significa un alias. `ignore` existe porque un ticket trae cosas que no son
# comida — bolsas de basura, pañales, discos desmaquillantes — y sin poder
# recordar "esto no va a la despensa" el usuario descartaría las mismas líneas
# en cada compra.
ALIAS_KINDS = ("product", "ignore")

# Comercio "cualquiera". Se usa cadena vacía y no NULL a propósito: en SQL dos
# NULL no son iguales, así que un índice único sobre una columna nullable no
# impide duplicados, que es justo lo que aquí hace falta impedir.
ANY_STORE = ""


class ProductAlias(Base):
    """Lo que pone el ticket ↔ qué producto es. El corazón de la feature.

    Un ticket no dice `Leche semidesnatada`, dice `LECHE SEM DESN 1L`, y en
    Mercadona `CAP. RISTRETTO ALUM` son cápsulas de café. Ningún emparejador
    genérico acierta eso. Lo que sí funciona es recordarlo: la primera compra
    cuesta correcciones y las siguientes casi ninguna.

    `user_id` nulo = alias global, aportado por el uso de todo el mundo. De
    momento solo se escriben los personales; promoverlos es cosa de la fase B.
    """

    __tablename__ = "product_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Los mismos nombres cambian entre cadenas, así que el alias es por comercio.
    store: Mapped[str] = mapped_column(String(64), nullable=False, default=ANY_STORE)
    # Texto del ticket ya normalizado (mayúsculas, sin tildes, sin cantidades).
    # Guardarlo normalizado es lo que permite buscarlo con un índice en vez de
    # recorriendo y normalizando cada fila.
    raw_text_norm: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="product")
    # Nulo cuando kind == 'ignore': no hay producto al que apuntar.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    times_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        # Dos índices parciales en vez de uno único: `user_id` es nullable y en
        # SQL NULL != NULL, así que un único constraint dejaría meter el mismo
        # alias global mil veces sin protestar.
        Index(
            "uq_alias_user",
            "user_id", "store", "raw_text_norm",
            unique=True,
            sqlite_where=user_id.isnot(None),
            postgresql_where=user_id.isnot(None),
        ),
        Index(
            "uq_alias_global",
            "store", "raw_text_norm",
            unique=True,
            sqlite_where=user_id.is_(None),
            postgresql_where=user_id.is_(None),
        ),
        Index("ix_alias_lookup", "raw_text_norm", "store"),
    )


class ReceiptImport(Base):
    """Una tanda: un ticket escaneado y aplicado a la despensa.

    Existe sobre todo para poder **deshacerla entera de un toque**. Una
    importación mal aceptada mete diez cosas mal a la vez, y desenredarlas a mano
    desde la despensa es odioso; los logs de compra ya existían, solo les faltaba
    saber de qué tanda venían.
    """

    __tablename__ = "receipt_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Fecha del ticket, no de la importación: se escanea el ticket de ayer.
    purchased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_receipt_imports_user_created", "user_id", "created_at"),)
