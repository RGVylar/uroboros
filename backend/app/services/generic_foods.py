"""Vuelca el catálogo de app/data/generic_foods.py en la tabla de productos.

Idempotente: inserta las claves nuevas y actualiza nombres y valores de las
que ya existen, sin tocar su id, así el diario que las usa sigue apuntando
bien. La llaman las migraciones y la base de datos de demo.

Va en SQL Core con las columnas escritas a mano, no con el modelo: una
migración antigua tiene que seguir funcionando aunque Product gane columnas
más adelante.
"""
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.data.generic_foods import GENERIC_FOODS

_products = sa.table(
    "products",
    sa.column("id", sa.Integer),
    sa.column("generic_key", sa.String),
    sa.column("name", sa.String),
    sa.column("name_en", sa.String),
    sa.column("name_pt", sa.String),
    sa.column("brand", sa.String),
    sa.column("calories_per_100g", sa.Float),
    sa.column("protein_per_100g", sa.Float),
    sa.column("carbs_per_100g", sa.Float),
    sa.column("fat_per_100g", sa.Float),
    sa.column("unit", sa.String),
    sa.column("source", sa.Enum(
        "openfoodfacts", "manual", "edited", "generic", name="product_source", create_type=False,
    )),
)


def sync_generic_foods(conn: Connection) -> int:
    existing = {
        row.generic_key
        for row in conn.execute(
            sa.select(_products.c.generic_key).where(_products.c.generic_key.is_not(None))
        )
    }
    inserts = []
    for key, es, en, pt, kcal, protein, carbs, fat, unit in GENERIC_FOODS:
        values = {
            "name": es, "name_en": en, "name_pt": pt, "brand": None,
            "calories_per_100g": kcal, "protein_per_100g": protein,
            "carbs_per_100g": carbs, "fat_per_100g": fat, "unit": unit,
        }
        if key in existing:
            conn.execute(_products.update().where(_products.c.generic_key == key).values(**values))
        else:
            inserts.append({**values, "generic_key": key, "source": "generic"})
    if inserts:
        conn.execute(_products.insert(), inserts)
    return len(GENERIC_FOODS)
