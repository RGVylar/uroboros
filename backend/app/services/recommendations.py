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
    def __init__(self, product: Product, suggested_grams: int, reason: str):
        self.product = product
        self.suggested_grams = suggested_grams
        self.reason = reason
        self.estimated_calories = product.calories_per_100g * suggested_grams / 100


def get_recommendations(db: Session, user: User, today: date) -> list[ProductRecommendation]:
    """Get intelligent food recommendations based on remaining calories and consumption history"""

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

    # Count frequency of each product
    product_frequency: dict[int, int] = {}
    for entry in past_entries:
        product_frequency[entry.product_id] = product_frequency.get(entry.product_id, 0) + 1

    # Get top products (excluding those already logged today)
    today_product_ids = {e.product_id for e in today_entries}
    recommendations = []

    for product_id in sorted(
        product_frequency.keys(),
        key=lambda pid: product_frequency[pid],
        reverse=True
    )[:10]:  # Top 10 most frequent
        if product_id in today_product_ids:
            continue

        product = db.get(Product, product_id)
        if not product:
            continue

        # Suggest portion size based on remaining calories
        # Try to stay under 1/3 of remaining calories
        suggested_grams = int(
            min(
                300,  # Cap at 300g for practical portion sizes
                max(
                    50,  # Minimum 50g
                    (remaining_calories / 3) * 100 / product.calories_per_100g
                )
            )
        )

        freq = product_frequency[product_id]
        reason = f"Eaten {freq} times in past 30 days"

        recommendations.append(
            ProductRecommendation(product, suggested_grams, reason)
        )

        if len(recommendations) >= 5:
            break

    return recommendations


def get_frequently_used_products(db: Session, user: User, limit: int = 10) -> list[FrequentlyUsedProduct]:
    """Get user's most frequently logged products (all time)"""

    # Get all entries for the user, ordered by recency
    entries = list(
        db.scalars(
            select(DiaryEntry)
            .where(DiaryEntry.user_id == user.id)
            .order_by(DiaryEntry.consumed_at.desc())
        )
    )

    # Count frequency of each product
    product_frequency: dict[int, int] = {}
    for entry in entries:
        product_frequency[entry.product_id] = product_frequency.get(entry.product_id, 0) + 1

    # Get top products with their details
    frequently_used = []
    for product_id in sorted(
        product_frequency.keys(),
        key=lambda pid: product_frequency[pid],
        reverse=True
    )[:limit]:
        product = db.get(Product, product_id)
        if product:
            frequently_used.append(
                FrequentlyUsedProduct(product, product_frequency[product_id])
            )

    return frequently_used
