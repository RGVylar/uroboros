"""Rellena la cuenta del revisor de Google Play con datos de ejemplo.

Google revisa la app entrando con las credenciales que le damos en «Datos de
inicio de sesión». Una cuenta recién creada está vacía y la mitad de la app no
se ve: sin diario no hay anillos de macros ni historial, sin peso no hay
tendencia, y sin premium los routers de medidas, ejercicio, cheat days y export
responden 403 `premium_required`. Lo que no se ve se rechaza más fácil, así que
este script deja la cuenta como la de alguien que lleva tres semanas usándola.

**No crea la cuenta**: regístrala tú desde la app o la web y luego pasa su email.
Así el alta pasa por el flujo normal (hash de contraseña, código de invitación)
y este script solo siembra.

Uso, desde el host Proxmox:

    pct exec 200 -- bash -c "cd /opt/uroboros/backend && \
        .venv/bin/python scripts/seed_reviewer_account.py revision.play@ejemplo.com"

Es idempotente: si la cuenta ya tiene diario, no duplica nada. Para rehacerla
desde cero, pásale --reset.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.body_measurement import BodyMeasurementLog  # noqa: E402
from app.models.diary import DiaryEntry, MealType  # noqa: E402
from app.models.exercise import Exercise, ExerciseSession, ExerciseSessionEntry  # noqa: E402
from app.models.goals import UserGoals  # noqa: E402
from app.models.product import Product, ProductSource  # noqa: E402
from app.models.recipe import Recipe, RecipeIngredient, RecipeScope  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.water import WaterLog  # noqa: E402
from app.models.weight import WeightLog  # noqa: E402

DAYS = 21

# Objetivos de alguien que mantiene peso. Los macros suman ~2100 kcal, así que
# el día cuadra y los anillos no salen descuadrados en la captura.
GOALS = dict(kcal=2100, protein=150, carbs=210, fat=65, water_ml=2500)

# (nombre, marca, kcal, prot, carbs, grasa) por 100 g. Productos que ya existan
# por nombre se reutilizan: la tabla de productos es global, no del usuario.
PRODUCTS = [
    ("Avena en copos", None, 375, 13.0, 60.0, 7.0),
    ("Yogur griego natural", None, 97, 9.0, 4.0, 5.0),
    ("Plátano", None, 89, 1.1, 23.0, 0.3),
    ("Pechuga de pavo a la plancha", None, 135, 29.0, 0.0, 1.5),
    ("Arroz integral cocido", None, 123, 2.6, 26.0, 1.0),
    ("Lentejas cocidas", None, 116, 9.0, 20.0, 0.4),
    ("Salmón al horno", None, 208, 20.0, 0.0, 13.0),
    ("Brócoli hervido", None, 35, 2.4, 7.0, 0.4),
    ("Aceite de oliva virgen extra", None, 884, 0.0, 0.0, 100.0),
    ("Almendras crudas", None, 579, 21.0, 22.0, 50.0),
]

# Un día tipo: (producto, gramos, comida, hora). Suma ~2100 kcal.
DAY_PLAN = [
    ("Avena en copos", 70, MealType.breakfast, time(8, 30)),
    ("Yogur griego natural", 150, MealType.breakfast, time(8, 30)),
    ("Plátano", 120, MealType.breakfast, time(8, 35)),
    ("Pechuga de pavo a la plancha", 180, MealType.lunch, time(14, 0)),
    ("Arroz integral cocido", 200, MealType.lunch, time(14, 0)),
    ("Brócoli hervido", 150, MealType.lunch, time(14, 0)),
    ("Aceite de oliva virgen extra", 10, MealType.lunch, time(14, 0)),
    ("Almendras crudas", 25, MealType.snack, time(17, 30)),
    ("Salmón al horno", 160, MealType.dinner, time(21, 0)),
    ("Lentejas cocidas", 180, MealType.dinner, time(21, 0)),
]


def _macros(p: Product, grams: float) -> dict:
    f = grams / 100.0
    return dict(
        calories=round(p.calories_per_100g * f, 1),
        protein=round(p.protein_per_100g * f, 1),
        carbs=round(p.carbs_per_100g * f, 1),
        fat=round(p.fat_per_100g * f, 1),
    )


def _ensure_products(db) -> dict[str, Product]:
    out: dict[str, Product] = {}
    for name, brand, kcal, prot, carbs, fat in PRODUCTS:
        p = db.scalar(select(Product).where(Product.name == name))
        if not p:
            p = Product(
                name=name, brand=brand,
                calories_per_100g=kcal, protein_per_100g=prot,
                carbs_per_100g=carbs, fat_per_100g=fat,
                source=ProductSource.manual,
            )
            db.add(p)
            db.flush()
        out[name] = p
    return out


def _seed_diary(db, uid: int, products: dict[str, Product], today: date) -> int:
    n = 0
    for back in range(DAYS):
        d = today - timedelta(days=back)
        # Un par de días flojos, para que el historial no parezca generado:
        # una racha perfecta de 21 días llama más la atención que dos huecos.
        if back in (5, 13):
            continue
        for pname, grams, meal, at in DAY_PLAN:
            p = products[pname]
            db.add(DiaryEntry(
                user_id=uid, product_id=p.id, grams=float(grams),
                meal_type=meal,
                consumed_at=datetime.combine(d, at, tzinfo=timezone.utc),
                **_macros(p, grams),
            ))
            n += 1
    return n


def _seed_weight(db, uid: int, today: date) -> int:
    # Una bajada suave con ruido: 78.4 → ~77.3 en tres semanas.
    n = 0
    for back in range(0, DAYS, 3):
        d = today - timedelta(days=back)
        kg = 77.3 + (back * 0.05) + (0.2 if (back // 3) % 2 else -0.1)
        db.add(WeightLog(
            user_id=uid, weight=round(kg, 1),
            logged_at=datetime.combine(d, time(7, 30), tzinfo=timezone.utc),
        ))
        n += 1
    return n


def _seed_measurements(db, uid: int, today: date) -> int:
    n = 0
    for back, waist in ((18, 86.0), (9, 85.0), (1, 84.2)):
        d = today - timedelta(days=back)
        db.add(BodyMeasurementLog(
            user_id=uid,
            measurements={"waist": waist, "chest": 101.0, "hip": 97.5, "arm": 34.0, "thigh": 57.0},
            logged_at=datetime.combine(d, time(7, 45), tzinfo=timezone.utc),
        ))
        n += 1
    return n


def _seed_water(db, uid: int, today: date) -> int:
    n = 0
    for back in range(DAYS):
        d = today - timedelta(days=back)
        db.add(WaterLog(user_id=uid, ml=2250.0, logged_date=d))
        n += 1
    return n


def _seed_exercise(db, uid: int, today: date) -> int:
    ex = db.scalar(
        select(Exercise).where(Exercise.is_predefined.is_(True), Exercise.unit == "minutos")
    )
    if not ex:
        print("  · sin ejercicios predefinidos en la BD, me salto las sesiones")
        return 0
    n = 0
    for back, qty in ((16, 35.0), (11, 45.0), (6, 40.0), (2, 50.0)):
        d = today - timedelta(days=back)
        total = round(qty * ex.kcal_per_unit, 1)
        s = ExerciseSession(user_id=uid, session_date=d, total_calories=total)
        db.add(s)
        db.flush()
        db.add(ExerciseSessionEntry(
            session_id=s.id, exercise_id=ex.id, quantity=qty, calories=total,
        ))
        n += 1
    return n


def _seed_recipe(db, uid: int, products: dict[str, Product]) -> bool:
    if db.scalar(select(Recipe.id).where(Recipe.owner_id == uid).limit(1)):
        return False
    r = Recipe(
        name="Salmón con lentejas",
        owner_id=uid,
        share_scope=RecipeScope.none,
        total_weight=520.0,  # pesa menos que la suma: al horno pierde agua
    )
    db.add(r)
    db.flush()
    for pname, grams in (("Salmón al horno", 320), ("Lentejas cocidas", 250), ("Aceite de oliva virgen extra", 15)):
        db.add(RecipeIngredient(recipe_id=r.id, product_id=products[pname].id, grams=float(grams)))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("email", help="email de la cuenta del revisor (ya registrada)")
    ap.add_argument("--reset", action="store_true",
                    help="borra los datos sembrados antes de volver a sembrar")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == args.email))
        if not user:
            print(f"✗ No existe ninguna cuenta con el email {args.email!r}.")
            print("  Regístrala primero desde la app o la web y vuelve a ejecutar esto.")
            return 1

        uid = user.id
        print(f"Cuenta #{uid} · {user.email} · {user.name}")

        if args.reset:
            for model in (DiaryEntry, WeightLog, BodyMeasurementLog, WaterLog):
                db.execute(delete(model).where(model.user_id == uid))
            sids = db.scalars(select(ExerciseSession.id).where(ExerciseSession.user_id == uid)).all()
            if sids:
                db.execute(delete(ExerciseSessionEntry).where(ExerciseSessionEntry.session_id.in_(sids)))
            db.execute(delete(ExerciseSession).where(ExerciseSession.user_id == uid))
            rids = db.scalars(select(Recipe.id).where(Recipe.owner_id == uid)).all()
            if rids:
                db.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(rids)))
            db.execute(delete(Recipe).where(Recipe.owner_id == uid))
            db.commit()
            print("  · datos anteriores borrados (--reset)")

        # Acceso completo y sin caducidad. `grandfathered` y no `premium`: un
        # premium puede llevar fecha de expiración y un trial caduca solo, y que
        # se apague a mitad de revisión es justo el rechazo que intentamos evitar.
        if not user.grandfathered:
            user.grandfathered = True
            print("  · grandfathered = true (acceso completo, sin caducidad)")

        if not db.scalar(select(UserGoals).where(UserGoals.user_id == uid)):
            db.add(UserGoals(user_id=uid, inventory_enabled=True, **GOALS))
            print(f"  · objetivos: {GOALS['kcal']} kcal / {GOALS['protein']} g proteína")

        products = _ensure_products(db)
        today = datetime.now(timezone.utc).date()

        already = db.scalar(
            select(func.count()).select_from(DiaryEntry).where(DiaryEntry.user_id == uid)
        ) or 0
        if already:
            print(f"  · el diario ya tiene {already} entradas, no lo toco (usa --reset para rehacerlo)")
        else:
            print(f"  · diario: {_seed_diary(db, uid, products, today)} entradas en {DAYS} días")
            print(f"  · peso: {_seed_weight(db, uid, today)} registros")
            print(f"  · medidas: {_seed_measurements(db, uid, today)} registros")
            print(f"  · agua: {_seed_water(db, uid, today)} días")
            print(f"  · ejercicio: {_seed_exercise(db, uid, today)} sesiones")

        if _seed_recipe(db, uid, products):
            print("  · receta: «Salmón con lentejas» (con peso final, para la ración en gramos)")

        db.commit()
        print("✓ Listo. Entra con esa cuenta y comprueba que se ve todo antes de mandar la revisión.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
