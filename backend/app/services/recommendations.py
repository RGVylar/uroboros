from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DiaryEntry, Product, User, UserGoals


class FrequentlyUsedProduct:
    """Product with usage count"""
    def __init__(self, product: Product, count: int):
        self.product = product
        self.count = count


class ProductRecommendation:
    """Recommendation with suggested portion size"""
    def __init__(self, product: Product, suggested_grams: int, reason_kind: str,
                 reason_freq: int, reason_macro_per_100g: float | None = None):
        self.product = product
        self.suggested_grams = suggested_grams
        self.reason_kind = reason_kind
        self.reason_freq = reason_freq
        self.reason_macro_per_100g = reason_macro_per_100g
        self.estimated_calories = product.calories_per_100g * suggested_grams / 100


# Macro focus: attribute on Product / UserGoals / DiaryEntry, and Spanish label
MACRO_FOCUS = {
    "protein": ("protein_per_100g", "protein", "proteína"),
    "carbs": ("carbs_per_100g", "carbs", "carbohidratos"),
    "fat": ("fat_per_100g", "fat", "grasa"),
}


def get_recommendations(
    db: Session, user: User, today: date, focus: str = "kcal"
) -> list[ProductRecommendation]:
    """Get intelligent food recommendations based on remaining calories (or a
    remaining macro, when focus is protein/carbs/fat) and consumption history"""

    # Get user's goals
    goals = db.get(UserGoals, user.id)
    if not goals:
        return []

    # Get today's consumption
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = datetime.combine(today, time.max, tzinfo=timezone.utc)
    today_entries = list(
        db.scalars(
            select(DiaryEntry).where(
                DiaryEntry.user_id == user.id,
                DiaryEntry.consumed_at >= start,
                DiaryEntry.consumed_at <= end,
            )
        )
    )

    consumed_calories = sum(e.calories for e in today_entries)
    remaining_calories = max(0, goals.kcal - consumed_calories)

    # If almost at limit, no recommendations
    if remaining_calories < 100:
        return []

    remaining_macro = 0.0
    if focus in MACRO_FOCUS:
        per_100g_attr, goal_attr, _ = MACRO_FOCUS[focus]
        consumed_macro = sum(getattr(e, goal_attr) for e in today_entries)
        remaining_macro = max(0.0, getattr(goals, goal_attr) - consumed_macro)
        # Macro goal already met: nothing useful to suggest
        if remaining_macro < 5:
            return []

    # Get user's most frequently consumed products in past 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    past_entries = list(
        db.scalars(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user.id,
                DiaryEntry.consumed_at >= thirty_days_ago,
            )
            .order_by(DiaryEntry.consumed_at.desc())
        )
    )

    # Count frequency of each product (products already loaded via lazy="joined")
    product_frequency: dict[int, int] = {}
    product_by_id: dict[int, Product] = {}
    for entry in past_entries:
        product_frequency[entry.product_id] = product_frequency.get(entry.product_id, 0) + 1
        if entry.product_id not in product_by_id and entry.product:
            product_by_id[entry.product_id] = entry.product

    # Get top products (excluding those already logged today)
    today_product_ids = {e.product_id for e in today_entries}
    recommendations = []

    if focus in MACRO_FOCUS:
        per_100g_attr, _, label = MACRO_FOCUS[focus]
        # Rank by macro density (grams of macro per 100 kcal), so the foods
        # that best fill the remaining macro without spending calories win
        def density(pid: int) -> float:
            p = product_by_id.get(pid)
            if not p:
                return 0.0
            macro = getattr(p, per_100g_attr)
            return macro / max(p.calories_per_100g, 1.0)

        candidate_ids = sorted(
            product_frequency.keys(),
            key=lambda pid: (density(pid), product_frequency[pid]),
            reverse=True,
        )
    else:
        candidate_ids = sorted(
            product_frequency.keys(),
            key=lambda pid: product_frequency[pid],
            reverse=True,
        )[:10]  # Top 10 most frequent

    for product_id in candidate_ids:
        if product_id in today_product_ids:
            continue

        product = product_by_id.get(product_id)
        if not product:
            continue

        freq = product_frequency[product_id]

        if focus in MACRO_FOCUS:
            per_100g_attr, _, label = MACRO_FOCUS[focus]
            macro_per_100g = getattr(product, per_100g_attr)
            if macro_per_100g <= 0:
                continue

            # Portion that covers ~1/3 of the remaining macro...
            suggested_grams = (remaining_macro / 3) * 100 / macro_per_100g
            # ...without blowing past the remaining calories
            if product.calories_per_100g > 0:
                suggested_grams = min(
                    suggested_grams,
                    remaining_calories * 100 / product.calories_per_100g,
                )
            suggested_grams = int(min(300, max(50, suggested_grams)))

            # El texto lo monta el cliente: aqui solo salen los datos, para que
            # la frase pueda estar en el idioma del usuario sin que el backend
            # sepa cual es.
            reason_kind = "macro"
        else:
            # Suggest portion size based on remaining calories
            # Try to stay under 1/3 of remaining calories
            if product.calories_per_100g > 0:
                suggested_grams = int(
                    min(
                        300,  # Cap at 300g for practical portion sizes
                        max(
                            50,  # Minimum 50g
                            (remaining_calories / 3) * 100 / product.calories_per_100g
                        )
                    )
                )
            else:
                # Zero-calorie products (water, diet drinks): portion can't be
                # derived from calories, use a standard serving
                suggested_grams = 100

            reason_kind = "freq"
            macro_per_100g = None

        recommendations.append(
            ProductRecommendation(product, suggested_grams, reason_kind, freq, macro_per_100g)
        )

        if len(recommendations) >= 5:
            break

    return recommendations


def get_frequently_used_products(db: Session, user: User, limit: int = 10) -> list[FrequentlyUsedProduct]:
    """Get user's most frequently logged products (all time).

    Was: load every diary entry the user ever logged (hydrated with the
    joined product) and count in Python — O(full history) on every dashboard
    and Add-food page load. Now: GROUP BY in SQL (uses ix_diary_entries_user_id)
    to get just the top `limit` product ids/counts, then a single IN query for
    the product rows. Two fixed queries regardless of history size; same
    response shape."""
    rows = db.execute(
        select(DiaryEntry.product_id, func.count(DiaryEntry.id).label("cnt"))
        .where(DiaryEntry.user_id == user.id)
        .group_by(DiaryEntry.product_id)
        .order_by(func.count(DiaryEntry.id).desc())
        .limit(limit)
    ).all()

    if not rows:
        return []

    products = {
        p.id: p
        for p in db.scalars(
            select(Product).where(Product.id.in_([row.product_id for row in rows]))
        )
    }

    return [
        FrequentlyUsedProduct(products[row.product_id], row.cnt)
        for row in rows
        if row.product_id in products
    ]
