"""Módulos de la app: qué partes ve cada usuario.

Hay dos clases de módulo y el frontend no tiene por qué saberlo:

- **De interfaz** (agua, peso, ánimo…): solo deciden qué se enseña. Viven en
  `users.modules`, que guarda únicamente lo que el usuario ha tocado.
- **Con efecto en el backend** (cheat days, inventario): son columnas
  de `user_goals` que el servidor ya consulta, así que se leen y escriben ahí.

`GET/PATCH /users/me/modules` devuelve y acepta las dos mezcladas.
"""
from sqlalchemy.orm import Session

from app.models import User, UserGoals

# Valor por defecto de cada módulo de interfaz. El ánimo empezó escondido y así
# sigue; el resto ya se veía siempre, y apagarlo a quien ya usa la app sería
# quitarle algo sin avisar.
UI_MODULES: dict[str, bool] = {
    "water": True,
    "weight": True,
    "exercise": True,
    "measurements": True,
    "supplements": True,
    "mood": False,
}

# Módulo → columna de user_goals.
# La creatina fue módulo hasta la 1.28; ahora es un suplemento más (migración 0080).
GOAL_MODULES: dict[str, str] = {
    "cheat_days": "cheat_days_enabled",
    "inventory": "inventory_enabled",
}

# Para crear user_goals si alguien enciende un módulo antes de tener objetivos
# (se saltó el onboarding). Los mismos que pone el frontend en ese caso.
_DEFAULT_GOALS = {"kcal": 2000, "protein": 150, "carbs": 250, "fat": 65}


def get_modules(db: Session, user: User) -> dict[str, bool]:
    stored = user.modules or {}
    out = {k: bool(stored.get(k, default)) for k, default in UI_MODULES.items()}
    goals = db.get(UserGoals, user.id)
    for key, column in GOAL_MODULES.items():
        out[key] = bool(getattr(goals, column)) if goals else False
    return out


def set_modules(db: Session, user: User, changes: dict[str, bool]) -> dict[str, bool]:
    """Aplica los cambios que lleguen; los que no, se quedan como estaban."""
    ui = {k: v for k, v in changes.items() if k in UI_MODULES}
    if ui:
        # Objeto nuevo, no mutar el existente: SQLAlchemy no detecta cambios
        # dentro de una columna JSON.
        user.modules = {**(user.modules or {}), **ui}

    goal_changes = {GOAL_MODULES[k]: v for k, v in changes.items() if k in GOAL_MODULES}
    if goal_changes:
        goals = db.get(UserGoals, user.id)
        if goals is None:
            goals = UserGoals(user_id=user.id, **_DEFAULT_GOALS)
            db.add(goals)
        for column, value in goal_changes.items():
            setattr(goals, column, value)

    db.commit()
    db.refresh(user)
    return get_modules(db, user)
