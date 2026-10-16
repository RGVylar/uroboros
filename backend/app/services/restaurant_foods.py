"""Vuelca la carta de app/data/restaurant_foods.py en la tabla de productos.

Igual que sync_generic_foods: idempotente, actualiza por clave sin tocar el id
(el diario que los usa sigue apuntando bien) y va en SQL Core para que una
migración antigua no dependa de cómo sea Product más adelante. Los productos
que la cadena retira no se borran: alguien puede tenerlos en el diario.
"""
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.data.restaurant_foods import RESTAURANT_FOODS

_products = sa.table(
    "products",
    sa.column("id", sa.Integer),
    sa.column("restaurant_key", sa.String),
    sa.column("name", sa.String),
    sa.column("brand", sa.String),
    sa.column("calories_per_100g", sa.Float),
    sa.column("protein_per_100g", sa.Float),
    sa.column("carbs_per_100g", sa.Float),
    sa.column("fat_per_100g", sa.Float),
    sa.column("unit", sa.String),
    sa.column("serving_qty", sa.Float),
    sa.column("source", sa.Enum(
        "openfoodfacts", "manual", "edited", "generic", "restaurant",
        name="product_source", create_type=False,
    )),
)


def sync_restaurant_foods(conn: Connection) -> int:
    existing = {
        row.restaurant_key
        for row in conn.execute(
            sa.select(_products.c.restaurant_key).where(_products.c.restaurant_key.is_not(None))
        )
    }
    inserts = []
    for key, chain, name, kcal, protein, carbs, fat, unit, serving in RESTAURANT_FOODS:
        values = {
            "name": name, "brand": chain,
            "calories_per_100g": kcal, "protein_per_100g": protein,
            "carbs_per_100g": carbs, "fat_per_100g": fat,
            "unit": unit, "serving_qty": serving,
        }
        if key in existing:
            conn.execute(_products.update().where(_products.c.restaurant_key == key).values(**values))
        else:
            inserts.append({**values, "restaurant_key": key, "source": "restaurant"})
    if inserts:
        conn.execute(_products.insert(), inserts)
    return len(RESTAURANT_FOODS)
