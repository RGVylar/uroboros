"""
Seed script: inserts common Spanish foods into the products table.
Run from the backend/ directory:
    python seed_products.py
Uses the same DATABASE_URL as the app (set via env var or .env).
"""

import os
import sys

# Allow running from the backend/ directory
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.product import Product, ProductSource

FOODS = [
    # ── Carnes ──────────────────────────────────────────────────────────────
    ("Pechuga de pollo (cruda)", None, 165, 31.0, 0.0, 3.6),
    ("Pechuga de pollo (cocida)", None, 165, 31.0, 0.0, 3.6),
    ("Muslo de pollo sin piel", None, 177, 24.0, 0.0, 9.0),
    ("Pollo a la plancha", None, 165, 31.0, 0.0, 3.6),
    ("Pechuga de pavo", None, 135, 30.0, 0.0, 1.0),
    ("Ternera magra", None, 187, 26.0, 0.0, 9.0),
    ("Lomo de cerdo", None, 182, 22.0, 0.0, 10.0),
    ("Solomillo de cerdo", None, 143, 22.0, 0.0, 6.0),
    ("Jamón serrano", None, 241, 30.0, 0.0, 14.0),
    ("Jamón cocido (pavo)", None, 107, 18.0, 2.0, 3.5),
    # ── Pescados y mariscos ──────────────────────────────────────────────────
    ("Salmón", None, 208, 20.0, 0.0, 13.0),
    ("Atún al natural (escurrido)", None, 116, 26.0, 0.0, 1.0),
    ("Atún en aceite (escurrido)", None, 198, 26.0, 0.0, 10.0),
    ("Merluza", None, 86, 17.0, 0.0, 2.0),
    ("Sardinas al natural", None, 208, 21.0, 0.0, 14.0),
    ("Gambas", None, 85, 18.0, 0.0, 1.0),
    ("Bacalao", None, 82, 18.0, 0.0, 0.7),
    ("Lubina", None, 97, 18.0, 0.0, 2.5),
    ("Dorada", None, 96, 18.0, 0.0, 3.0),
    ("Caballa", None, 205, 19.0, 0.0, 13.0),
    # ── Huevos ───────────────────────────────────────────────────────────────
    ("Huevo entero", None, 155, 13.0, 1.1, 11.0),
    ("Clara de huevo", None, 52, 11.0, 1.0, 0.2),
    ("Yema de huevo", None, 322, 16.0, 3.6, 27.0),
    # ── Lácteos ──────────────────────────────────────────────────────────────
    ("Leche entera", None, 61, 3.2, 4.8, 3.3),
    ("Leche semidesnatada", None, 47, 3.3, 4.8, 1.5),
    ("Leche desnatada", None, 35, 3.4, 5.0, 0.1),
    ("Leche sin lactosa semidesnatada", None, 47, 3.3, 4.8, 1.5),
    ("Leche de coco", None, 230, 2.3, 5.5, 23.0),
    ("Leche de avena", None, 47, 1.0, 9.0, 1.5),
    ("Leche de almendra", None, 17, 0.6, 1.5, 1.0),
    ("Yogur natural entero", None, 59, 3.5, 4.7, 3.3),
    ("Yogur natural desnatado", None, 35, 3.6, 4.9, 0.2),
    ("Yogur griego", None, 97, 9.0, 4.0, 5.0),
    ("Yogur griego 0%", None, 57, 10.0, 4.0, 0.2),
    ("Queso fresco batido 0%", None, 60, 9.5, 3.0, 0.5),
    ("Queso cottage", None, 98, 11.0, 3.4, 4.3),
    ("Queso mozzarella", None, 280, 18.0, 2.2, 22.0),
    ("Queso manchego curado", None, 395, 26.0, 1.0, 32.0),
    ("Requesón", None, 134, 11.0, 3.0, 9.0),
    # ── Cereales y farináceos ─────────────────────────────────────────────────
    ("Arroz blanco (crudo)", None, 360, 7.0, 79.0, 0.6),
    ("Arroz blanco (cocido)", None, 130, 2.7, 28.0, 0.3),
    ("Arroz integral (crudo)", None, 350, 7.5, 73.0, 2.7),
    ("Arroz integral (cocido)", None, 123, 2.7, 25.0, 1.0),
    ("Pasta (cruda)", None, 371, 13.0, 72.0, 1.5),
    ("Pasta (cocida)", None, 131, 5.0, 25.0, 1.1),
    ("Pasta integral (cruda)", None, 352, 14.0, 68.0, 2.5),
    ("Pasta integral (cocida)", None, 124, 5.2, 23.0, 1.0),
    ("Avena en copos", None, 389, 17.0, 66.0, 7.0),
    ("Pan blanco", None, 265, 9.0, 49.0, 3.0),
    ("Pan integral", None, 247, 13.0, 41.0, 3.4),
    ("Pan de centeno", None, 259, 8.5, 48.0, 3.3),
    ("Tortilla de trigo (wraps)", None, 310, 8.0, 52.0, 8.0),
    ("Maíz dulce (cocido)", None, 86, 3.2, 19.0, 1.2),
    ("Quinoa (cocida)", None, 120, 4.4, 22.0, 1.9),
    ("Cuscús (cocido)", None, 112, 3.8, 23.0, 0.6),
    # ── Legumbres ─────────────────────────────────────────────────────────────
    ("Lentejas (cocidas)", None, 116, 9.0, 20.0, 0.4),
    ("Garbanzos (cocidos)", None, 164, 8.9, 27.0, 2.6),
    ("Alubias blancas (cocidas)", None, 127, 8.7, 22.0, 0.5),
    ("Alubias negras (cocidas)", None, 132, 8.9, 24.0, 0.5),
    ("Edamame", None, 122, 11.0, 10.0, 5.0),
    # ── Verduras y hortalizas ────────────────────────────────────────────────
    ("Pimiento rojo", None, 31, 1.0, 6.0, 0.3),
    ("Pimiento verde", None, 20, 0.9, 4.0, 0.2),
    ("Pimiento amarillo", None, 27, 1.0, 6.3, 0.2),
    ("Cebolla", None, 40, 1.1, 9.0, 0.1),
    ("Cebolla morada", None, 42, 1.2, 9.6, 0.1),
    ("Zanahoria", None, 41, 0.9, 10.0, 0.2),
    ("Tomate", None, 18, 0.9, 3.9, 0.2),
    ("Tomate cherry", None, 18, 0.9, 3.9, 0.2),
    ("Lechuga", None, 15, 1.4, 2.1, 0.2),
    ("Espinacas", None, 23, 2.9, 3.6, 0.4),
    ("Brócoli", None, 34, 2.8, 6.6, 0.4),
    ("Coliflor", None, 25, 2.0, 5.0, 0.3),
    ("Calabacín", None, 17, 1.2, 3.1, 0.3),
    ("Berenjena", None, 25, 1.0, 5.9, 0.2),
    ("Pepino", None, 16, 0.7, 3.6, 0.1),
    ("Ajo", None, 149, 6.4, 33.0, 0.5),
    ("Patata", None, 77, 2.0, 17.0, 0.1),
    ("Boniato / Batata", None, 86, 1.6, 20.0, 0.1),
    ("Champiñones", None, 22, 3.1, 3.3, 0.3),
    ("Col / Repollo", None, 25, 1.3, 5.8, 0.1),
    ("Apio", None, 16, 0.7, 3.0, 0.2),
    ("Puerro", None, 61, 1.5, 14.0, 0.3),
    ("Rúcula", None, 25, 2.6, 3.7, 0.7),
    ("Aguacate", None, 160, 2.0, 9.0, 15.0),
    ("Maíz en lata (escurrido)", None, 86, 3.2, 19.0, 1.2),
    ("Tomate triturado (bote)", None, 24, 1.1, 4.8, 0.2),
    # ── Frutas ────────────────────────────────────────────────────────────────
    ("Manzana", None, 52, 0.3, 14.0, 0.2),
    ("Plátano", None, 89, 1.1, 23.0, 0.3),
    ("Naranja", None, 47, 0.9, 12.0, 0.1),
    ("Mandarina", None, 53, 0.8, 13.0, 0.3),
    ("Pomelo", None, 42, 0.8, 11.0, 0.1),
    ("Limón", None, 29, 1.1, 9.0, 0.3),
    ("Fresa", None, 32, 0.7, 7.7, 0.3),
    ("Kiwi", None, 61, 1.1, 15.0, 0.5),
    ("Pera", None, 57, 0.4, 15.0, 0.1),
    ("Uva", None, 69, 0.7, 18.0, 0.2),
    ("Sandía", None, 30, 0.6, 7.6, 0.2),
    ("Melón", None, 34, 0.8, 8.0, 0.2),
    ("Mango", None, 60, 0.8, 15.0, 0.4),
    ("Piña", None, 50, 0.5, 13.0, 0.1),
    ("Arándanos", None, 57, 0.7, 14.0, 0.3),
    ("Frambuesa", None, 52, 1.2, 11.9, 0.7),
    ("Cereza", None, 63, 1.1, 16.0, 0.2),
    ("Melocotón", None, 39, 0.9, 10.0, 0.3),
    ("Ciruela", None, 46, 0.7, 11.0, 0.3),
    ("Higo", None, 74, 0.8, 19.0, 0.3),
    ("Granada", None, 83, 1.7, 19.0, 1.2),
    # ── Aceites y grasas ──────────────────────────────────────────────────────
    ("Aceite de oliva virgen extra", None, 884, 0.0, 0.0, 100.0),
    ("Aceite de girasol", None, 884, 0.0, 0.0, 100.0),
    ("Aceite de coco", None, 862, 0.0, 0.0, 100.0),
    ("Mantequilla", None, 717, 0.9, 0.1, 81.0),
    # ── Frutos secos y semillas ──────────────────────────────────────────────
    ("Almendras", None, 579, 21.0, 22.0, 50.0),
    ("Nueces", None, 654, 15.0, 14.0, 65.0),
    ("Cacahuetes", None, 567, 26.0, 16.0, 49.0),
    ("Anacardos", None, 553, 18.0, 30.0, 44.0),
    ("Avellanas", None, 628, 15.0, 17.0, 61.0),
    ("Pistachos", None, 562, 20.0, 28.0, 45.0),
    ("Semillas de chía", None, 486, 17.0, 42.0, 31.0),
    ("Semillas de lino", None, 534, 18.0, 29.0, 42.0),
    ("Semillas de girasol", None, 584, 21.0, 20.0, 51.0),
    ("Mantequilla de cacahuete", None, 588, 25.0, 20.0, 50.0),
    # ── Otros comunes ─────────────────────────────────────────────────────────
    ("Aceitunas negras", None, 145, 1.0, 3.8, 15.0),
    ("Aceitunas verdes", None, 115, 0.8, 1.3, 12.0),
    ("Hummus", None, 177, 8.0, 14.0, 11.0),
    ("Salsa de tomate casera", None, 29, 1.5, 5.5, 0.3),
    ("Miel", None, 304, 0.3, 82.0, 0.0),
    ("Azúcar blanco", None, 387, 0.0, 100.0, 0.0),
    ("Chocolate negro 70%", None, 598, 8.0, 46.0, 43.0),
    ("Proteína whey", None, 380, 80.0, 7.0, 5.0),
    ("Tortilla de maíz", None, 218, 5.7, 46.0, 2.5),
    ("Salsa de soja", None, 53, 8.0, 5.0, 0.6),
]


def main():
    if settings.demo_mode:
        print("ERROR: No ejecutes este script en modo demo (usa DATABASE_URL de producción).")
        sys.exit(1)

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"client_encoding": "utf8"},
    )
    Session = sessionmaker(bind=engine)
    db = Session()

    inserted = 0
    skipped = 0

    for name, brand, kcal, prot, carbs, fat in FOODS:
        exists = db.scalar(select(Product).where(Product.name == name))
        if exists:
            skipped += 1
            continue
        db.add(Product(
            name=name,
            brand=brand,
            calories_per_100g=kcal,
            protein_per_100g=prot,
            carbs_per_100g=carbs,
            fat_per_100g=fat,
            source=ProductSource.manual,
        ))
        inserted += 1

    db.commit()
    db.close()
    print(f"Hecho: {inserted} alimentos insertados, {skipped} ya existían.")


if __name__ == "__main__":
    main()
