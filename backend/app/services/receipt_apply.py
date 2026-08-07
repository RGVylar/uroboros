"""Volcar un ticket revisado a la despensa, y poder deshacerlo entero.

Lo que llega aquí ya lo confirmó una persona en la pantalla de revisión: este
módulo no adivina nada. Su trabajo es escribir bien y dejar rastro suficiente
para desandarlo.

El deshacer no es un extra. Una importación mete diez cosas de golpe, así que
cuando sale mal sale mal diez veces, y desenredarlo a mano desde la despensa es
mucho peor que haberlo tecleado. Por eso cada movimiento queda atado a su tanda
(`inventory_logs.receipt_import_id`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    InventoryItem,
    InventoryLog,
    ReceiptImport,
    SharedInventoryItem,
    User,
)
from app.services.household import active_household
from app.services.receipt_matcher import remember
from app.services.unit_conversions import to_grams

# Qué hacer con cada línea revisada.
ACTIONS = ("add", "ignore", "skip")


@dataclass
class LineToApply:
    raw: str
    action: str
    product_id: int | None = None
    quantity: float = 1.0
    unit: str = "unit"
    location: str = "pantry"
    price_per_100g: float | None = None


def _add_stock(
    db: Session,
    user: User,
    line: LineToApply,
    import_id: int,
) -> None:
    """Suma stock y deja el log de compra atado a esta importación.

    Sigue la misma regla que el resto de la despensa: si hay pareja activa, todo
    va al inventario compartido. No se pregunta, igual que en `GET /inventory`.
    """
    friendship = active_household(db, user.id)
    delta_g = to_grams(db, line.quantity, line.unit, line.product_id)

    if friendship:
        existing = db.scalar(
            select(SharedInventoryItem).where(
                SharedInventoryItem.friendship_id == friendship.id,
                SharedInventoryItem.product_id == line.product_id,
            )
        )
        if existing is None:
            existing = SharedInventoryItem(
                friendship_id=friendship.id,
                product_id=line.product_id,
                quantity_g=0.0,
                quantity_base=0.0,
                unit=line.unit,
                location=line.location,
                added_by_user_id=user.id,
            )
            db.add(existing)
        item_id = None
    else:
        existing = db.scalar(
            select(InventoryItem).where(
                InventoryItem.user_id == user.id,
                InventoryItem.product_id == line.product_id,
            )
        )
        if existing is None:
            existing = InventoryItem(
                user_id=user.id,
                product_id=line.product_id,
                quantity_g=0.0,
                quantity_base=0.0,
                unit=line.unit,
                location=line.location,
            )
            db.add(existing)
        item_id = None

    # Sumar en la unidad que ya tenía; si no coinciden, gramos manda — es la
    # única forma de sumar peras con unidades sin mentir.
    if existing.unit == line.unit:
        existing.quantity_base += line.quantity
    else:
        existing.quantity_base = existing.quantity_g + delta_g
        existing.unit = "g"
    existing.quantity_g += delta_g
    existing.location = line.location
    if line.price_per_100g is not None:
        existing.price_per_100g = line.price_per_100g
    existing.updated_at = datetime.now(timezone.utc)

    db.flush()
    if isinstance(existing, InventoryItem):
        item_id = existing.id

    db.add(
        InventoryLog(
            user_id=user.id,
            item_id=item_id,
            product_id=line.product_id,
            quantity_change=line.quantity,
            unit=line.unit,
            quantity_base_change=delta_g,
            log_type="purchase",
            price_per_unit=line.price_per_100g,
            receipt_import_id=import_id,
        )
    )


def apply_receipt(
    db: Session,
    user: User,
    store: str,
    lines: list[LineToApply],
    purchased_at: datetime | None = None,
) -> ReceiptImport:
    """Escribe las líneas confirmadas y devuelve la tanda creada. Hace commit."""
    tanda = ReceiptImport(
        user_id=user.id,
        store=store or None,
        purchased_at=purchased_at,
        line_count=0,
    )
    db.add(tanda)
    db.flush()

    aplicadas = 0
    for line in lines:
        if line.action == "add" and line.product_id is not None:
            _add_stock(db, user, line, tanda.id)
            # Aprender va después de escribir: si el volcado falla, no queremos
            # haber memorizado una corrección que el usuario no llegó a ver.
            remember(db, user.id, store, line.raw, line.product_id, kind="product")
            aplicadas += 1
        elif line.action == "ignore":
            remember(db, user.id, store, line.raw, None, kind="ignore")
        # 'skip' no deja rastro a propósito: el usuario no ha decidido nada
        # sobre esa línea, y aprender un "no sé" la escondería la próxima vez.

    tanda.line_count = aplicadas
    db.commit()
    db.refresh(tanda)
    return tanda


def undo_receipt(db: Session, user: User, import_id: int) -> bool:
    """Deshace una importación entera. True si existía y era suya.

    Se resta lo que se sumó, no se pone a cero: entre la importación y el
    deshacer el usuario ha podido comerse parte de lo que compró, y machacar su
    stock sería peor que el error que viene a corregir.
    """
    tanda = db.scalar(
        select(ReceiptImport).where(
            ReceiptImport.id == import_id, ReceiptImport.user_id == user.id
        )
    )
    if tanda is None:
        return False

    friendship = active_household(db, user.id)
    logs = list(
        db.scalars(select(InventoryLog).where(InventoryLog.receipt_import_id == tanda.id))
    )

    for log in logs:
        if friendship:
            item = db.scalar(
                select(SharedInventoryItem).where(
                    SharedInventoryItem.friendship_id == friendship.id,
                    SharedInventoryItem.product_id == log.product_id,
                )
            )
        else:
            item = db.scalar(
                select(InventoryItem).where(
                    InventoryItem.user_id == user.id,
                    InventoryItem.product_id == log.product_id,
                )
            )
        if item is not None:
            item.quantity_g = max(0.0, item.quantity_g - log.quantity_base_change)
            if item.unit == log.unit:
                item.quantity_base = max(0.0, item.quantity_base - log.quantity_change)
            else:
                item.quantity_base = item.quantity_g
            if item.quantity_g <= 0 and item.quantity_base <= 0:
                # Se queda a cero: fuera. Deshacer tiene que dejarlo como si no
                # hubiera pasado, y una despensa llena de entradas vacías es
                # justo lo contrario. Para "esto lo quiero comprar" ya está la
                # lista de la compra, que es otra cosa.
                db.delete(item)
        db.delete(log)

    db.delete(tanda)
    db.commit()
    return True
