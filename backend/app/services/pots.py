"""Cuentas de una olla: cuánto ha comido cada uno y cuánto queda.

Lo comido se deduce del diario. Cada ración escala todos los ingredientes por
igual, así que la parte de la olla que lleva alguien es la suma de gramos de
sus entradas entre el peso en crudo de la olla. Si se borra una sola entrada
de una ración, la olla recupera exactamente esa parte.
"""
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DiaryEntry, Pot

# Por debajo de esto la olla se da por vacía (redondeos de float).
EMPTY_EPS = 1e-3


def eaten_fractions(db: Session, pot: Pot) -> tuple[dict[int, float], dict[tuple[date, int], float]]:
    """(fracción de la olla por usuario, fracción por día y usuario)."""
    raw = pot.raw_weight
    by_user: dict[int, float] = defaultdict(float)
    by_day: dict[tuple[date, int], float] = defaultdict(float)
    if raw <= 0:
        return by_user, by_day
    rows = db.execute(
        select(DiaryEntry.user_id, DiaryEntry.consumed_at, DiaryEntry.grams).where(DiaryEntry.pot_id == pot.id)
    ).all()
    for user_id, consumed_at, grams in rows:
        f = grams / raw
        by_user[user_id] += f
        by_day[(consumed_at.date(), user_id)] += f
    return by_user, by_day


def remaining_fraction(by_user: dict[int, float]) -> float:
    return max(0.0, 1.0 - sum(by_user.values()))


def pot_out(db: Session, pot: Pot) -> dict:
    by_user, by_day = eaten_fractions(db, pot)
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for ing in pot.ingredients:
        p, k = ing.product, ing.grams / 100.0
        totals["calories"] += p.calories_per_100g * k
        totals["protein"] += p.protein_per_100g * k
        totals["carbs"] += p.carbs_per_100g * k
        totals["fat"] += p.fat_per_100g * k
    s = pot.servings
    return {
        "id": pot.id,
        "name": pot.name,
        "owner_id": pot.owner_id,
        "partner_id": pot.partner_id,
        "servings": s,
        "cooked_weight": pot.cooked_weight,
        "raw_weight": pot.raw_weight,
        "created_at": pot.created_at,
        "finished_at": pot.finished_at,
        **{k: round(v, 1) for k, v in totals.items()},
        "ingredients": [
            {"id": i.id, "product_id": i.product_id, "name": i.product.display_name, "grams": i.grams}
            for i in pot.ingredients
        ],
        "eaten": [{"user_id": u, "servings": round(f * s, 2)} for u, f in by_user.items()],
        "days": [
            {"day": d, "user_id": u, "servings": round(f * s, 2)}
            for (d, u), f in sorted(by_day.items())
        ],
        "remaining": round(remaining_fraction(by_user) * s, 2),
    }
