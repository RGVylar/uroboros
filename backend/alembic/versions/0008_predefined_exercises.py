"""Add predefined exercises

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-12

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PREDEFINED = [
    # (name, kcal_per_unit, unit)
    # Cardio (por minuto)
    ("Correr (ritmo moderado)", 10.0, "minutos"),
    ("Correr (ritmo rápido)", 14.0, "minutos"),
    ("Ciclismo (moderado)", 8.0, "minutos"),
    ("Ciclismo (intenso)", 12.0, "minutos"),
    ("Natación", 9.0, "minutos"),
    ("Saltar la comba", 12.0, "minutos"),
    ("Caminata", 4.5, "minutos"),
    ("Elíptica", 9.0, "minutos"),
    ("Remo (máquina)", 10.0, "minutos"),
    # Fuerza (por repetición)
    ("Sentadilla", 0.5, "repeticiones"),
    ("Sentadilla con peso", 0.8, "repeticiones"),
    ("Flexiones", 0.4, "repeticiones"),
    ("Dominadas", 0.7, "repeticiones"),
    ("Press banca", 0.6, "repeticiones"),
    ("Peso muerto", 0.9, "repeticiones"),
    ("Zancadas", 0.4, "repeticiones"),
    ("Remo con barra", 0.6, "repeticiones"),
    ("Press militar", 0.5, "repeticiones"),
    ("Curl de bíceps", 0.3, "repeticiones"),
    ("Extensión de tríceps", 0.3, "repeticiones"),
    # HIIT / funcional (por repetición)
    ("Burpees", 0.8, "repeticiones"),
    ("Mountain climbers", 0.3, "repeticiones"),
    ("Jumping jacks", 0.2, "repeticiones"),
    ("Box jumps", 0.7, "repeticiones"),
    ("Kettlebell swing", 0.5, "repeticiones"),
    # Core
    ("Abdominales", 0.25, "repeticiones"),
    ("Plancha", 3.5, "minutos"),
    ("Russian twist", 0.2, "repeticiones"),
    # Otros
    ("Yoga / Stretching", 3.0, "minutos"),
    ("HIIT general", 13.0, "minutos"),
]


def upgrade() -> None:
    # Make user_id nullable and add is_predefined
    op.execute(
        "ALTER TABLE exercises ALTER COLUMN user_id DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS is_predefined BOOLEAN NOT NULL DEFAULT FALSE"
    )

    # Seed predefined exercises (user_id = NULL, is_predefined = TRUE)
    for name, kcal, unit in PREDEFINED:
        safe_name = name.replace("'", "''")
        safe_unit = unit.replace("'", "''")
        op.execute(
            f"INSERT INTO exercises (name, kcal_per_unit, unit, is_predefined, created_at, updated_at) "
            f"VALUES ('{safe_name}', {kcal}, '{safe_unit}', TRUE, NOW(), NOW())"
        )


def downgrade() -> None:
    op.execute("DELETE FROM exercises WHERE is_predefined = TRUE")
    op.execute("ALTER TABLE exercises DROP COLUMN IF EXISTS is_predefined")
    op.execute("ALTER TABLE exercises ALTER COLUMN user_id SET NOT NULL")
