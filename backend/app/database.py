from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _sqlite_add_column_if_missing(conn, table: str, column: str, col_def: str) -> None:
    """Add a column to a SQLite table if it doesn't already exist."""
    from sqlalchemy import text
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))


def _get_engine():
    # Import ALL models first so they're registered with Base (critical for create_all)
    # Import directly from submodules to avoid circular imports
    from app.models.user import User
    from app.models.product import Product, ProductSource
    from app.models.diary import DiaryEntry
    from app.models.recipe import Recipe, RecipeIngredient
    from app.models.weight import WeightLog
    from app.models.body_measurement import BodyMeasurementLog
    from app.models.goals import UserGoals
    from app.models.water import WaterLog
    from app.models.friendship import Friendship
    from app.models.creatine import CreatineLog
    from app.models.cheat_day import CheatDayLog
    from app.models.exercise import Exercise, ExerciseSession, ExerciseSessionEntry
    from app.models.inventory import InventoryItem, ShoppingListItem, SharedInventoryItem, SharedShoppingListItem
    from app.models.supplement import UserSupplement, SupplementLog
    from app.models.allergy import UserAllergy

    if settings.demo_mode:
        from app.security import hash_password
        import tempfile
        import os

        # SQLite on disk for demo/preview (survives multiple connections)
        temp_dir = tempfile.gettempdir()
        db_path = os.path.join(temp_dir, "uroboros_demo.db")
        # Remove old db if it exists (fresh demo each session)
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                # File might be in use by another process, skip deletion
                pass

        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create all tables and seed data (skip if running migrations)
        import os
        if os.getenv("ALEMBIC_MIGRATION") != "true":
            Base.metadata.create_all(engine)

            # Add any missing columns to existing SQLite tables (schema drift fix)
            with engine.connect() as conn:
                _sqlite_add_column_if_missing(conn, "user_goals", "cheat_days_enabled", "BOOLEAN NOT NULL DEFAULT 0")
                _sqlite_add_column_if_missing(conn, "user_goals", "inventory_enabled", "BOOLEAN NOT NULL DEFAULT 0")
                _sqlite_add_column_if_missing(conn, "exercises", "is_predefined", "BOOLEAN NOT NULL DEFAULT 0")
                _sqlite_add_column_if_missing(conn, "friendships", "shared_inventory_requester", "BOOLEAN NOT NULL DEFAULT 0")
                _sqlite_add_column_if_missing(conn, "friendships", "shared_inventory_receiver", "BOOLEAN NOT NULL DEFAULT 0")
                _sqlite_add_column_if_missing(conn, "friendships", "can_add_food_requester", "BOOLEAN NOT NULL DEFAULT 0")
                _sqlite_add_column_if_missing(conn, "user_goals", "macro_adjust_mode", "VARCHAR(20) NOT NULL DEFAULT 'off'")
                # Drop legacy column if it exists
                from sqlalchemy import text as _text
                cols = [r[1] for r in conn.execute(_text("PRAGMA table_info(friendships)")).fetchall()]
                if "shared_inventory" in cols:
                    conn.execute(_text("ALTER TABLE friendships DROP COLUMN shared_inventory"))
                conn.commit()

            # Seed demo data
            db = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

            # Create demo users (skip if they already exist)
            from sqlalchemy import select
            from app.models.friendship import Friendship, FriendshipStatus

            existing_user1 = db.scalar(select(User).where(User.email == "demo@demo.com"))
            existing_user2 = db.scalar(select(User).where(User.email == "demo2@demo.com"))
            existing_pilar = db.scalar(select(User).where(User.email == "pilar@demo.com"))

            if not existing_user1:
                user1 = User(email="demo@demo.com", password_hash=hash_password("demo1234"), name="Demo User")
                db.add(user1)
            else:
                user1 = existing_user1

            if not existing_user2:
                user2 = User(email="demo2@demo.com", password_hash=hash_password("demo1234"), name="Demo 2")
                db.add(user2)
            else:
                user2 = existing_user2

            if not existing_pilar:
                pilar = User(email="pilar@demo.com", password_hash=hash_password("demo1234"), name="Pilar")
                db.add(pilar)
            else:
                pilar = existing_pilar

            db.commit()
            if not existing_user1:
                db.refresh(user1)
            if not existing_user2:
                db.refresh(user2)
            if not existing_pilar:
                db.refresh(pilar)

            # Create demo friendship between Demo User and Pilar (accepted)
            existing_friendship = db.scalar(
                select(Friendship).where(
                    Friendship.requester_id == pilar.id,
                    Friendship.receiver_id == user1.id,
                )
            )
            if not existing_friendship:
                db.add(Friendship(
                    requester_id=pilar.id,
                    receiver_id=user1.id,
                    status=FriendshipStatus.accepted,
                    can_add_food=True,
                    can_add_food_requester=True,
                    shared_inventory_requester=False,
                    shared_inventory_receiver=False,
                ))
                db.commit()

            # Create demo goals for user1 (if not exist)
            existing_goals = db.scalar(select(UserGoals).where(UserGoals.user_id == user1.id))
            if not existing_goals:
                db.add(UserGoals(
                    user_id=user1.id,
                    kcal=2200,
                    protein=160,
                    carbs=220,
                    fat=70,
                    water_ml=2500,
                    track_creatine=False,
                    cheat_days_enabled=False,
                    inventory_enabled=True,
                ))
                db.commit()

            # Create demo products
            demo_products = [
                Product(
                    name="Pollo a la plancha",
                    brand="Casero",
                    calories_per_100g=165,
                    protein_per_100g=31,
                    carbs_per_100g=0,
                    fat_per_100g=3.6,
                    source=ProductSource.manual,
                ),
                Product(
                    name="Arroz blanco cocido",
                    brand=None,
                    calories_per_100g=130,
                    protein_per_100g=2.7,
                    carbs_per_100g=28,
                    fat_per_100g=0.3,
                    source=ProductSource.manual,
                ),
                Product(
                    name="Huevo",
                    brand=None,
                    calories_per_100g=155,
                    protein_per_100g=13,
                    carbs_per_100g=1.1,
                    fat_per_100g=11,
                    source=ProductSource.manual,
                ),
                Product(
                    name="Manzana roja",
                    brand=None,
                    calories_per_100g=52,
                    protein_per_100g=0.3,
                    carbs_per_100g=14,
                    fat_per_100g=0.2,
                    source=ProductSource.manual,
                ),
                Product(
                    name="Pechuga de pollo",
                    brand=None,
                    calories_per_100g=165,
                    protein_per_100g=31,
                    carbs_per_100g=0,
                    fat_per_100g=3.6,
                    source=ProductSource.manual,
                ),
                # Products with allergens for testing allergen detection
                Product(
                    name="Chocolate con leche",
                    brand="Milka",
                    calories_per_100g=535,
                    protein_per_100g=7.5,
                    carbs_per_100g=57,
                    fat_per_100g=30,
                    source=ProductSource.openfoodfacts,
                    allergens=["milk", "gluten", "nuts", "soybeans"],
                    ingredients_text="Azúcar, manteca de cacao, leche desnatada en polvo, cacao pasta, leche en polvo, suero de leche en polvo, avellanas, leche entera en polvo, emulgente (lecitina de soja), aromas.",
                ),
                Product(
                    name="Pan de molde",
                    brand="Bimbo",
                    calories_per_100g=265,
                    protein_per_100g=8,
                    carbs_per_100g=46,
                    fat_per_100g=5,
                    source=ProductSource.openfoodfacts,
                    allergens=["gluten", "milk", "soybeans"],
                    ingredients_text="Harina de trigo, agua, azúcar, aceite vegetal, levadura, sal, emulgentes (E471, lecitina de soja), conservante (E282), harina de soja.",
                ),
                Product(
                    name="Yogur natural",
                    brand="Danone",
                    calories_per_100g=61,
                    protein_per_100g=3.8,
                    carbs_per_100g=4.7,
                    fat_per_100g=3.1,
                    source=ProductSource.openfoodfacts,
                    allergens=["milk"],
                    ingredients_text="Leche entera pasteurizada, fermentos lácticos.",
                ),
            ]
            db.add_all(demo_products)
            db.commit()

            # Seed a demo allergy for user1 (milk) so allergen warnings show in demo
            existing_allergy = db.scalar(
                select(UserAllergy).where(UserAllergy.user_id == user1.id)
            )
            if not existing_allergy:
                db.add(UserAllergy(user_id=user1.id, ingredient="milk"))
                db.commit()

            # Seed predefined exercises (only if none exist yet)
            from sqlalchemy import select as sa_select, func
            existing_count = db.scalar(sa_select(func.count()).select_from(Exercise).where(Exercise.is_predefined == True))
            if not existing_count:
                predefined_exercises = [
                    # Cardio (por minuto)
                    Exercise(user_id=None, name="Correr (ritmo moderado)", kcal_per_unit=10.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Correr (ritmo rápido)", kcal_per_unit=14.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Ciclismo (moderado)", kcal_per_unit=8.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Ciclismo (intenso)", kcal_per_unit=12.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Natación", kcal_per_unit=9.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Saltar la comba", kcal_per_unit=12.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Caminata", kcal_per_unit=4.5, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Elíptica", kcal_per_unit=9.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Remo (máquina)", kcal_per_unit=10.0, unit="minutos", is_predefined=True),
                    # Fuerza (por repetición)
                    Exercise(user_id=None, name="Sentadilla", kcal_per_unit=0.5, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Sentadilla con peso", kcal_per_unit=0.8, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Flexiones", kcal_per_unit=0.4, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Dominadas", kcal_per_unit=0.7, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Press banca", kcal_per_unit=0.6, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Peso muerto", kcal_per_unit=0.9, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Zancadas", kcal_per_unit=0.4, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Remo con barra", kcal_per_unit=0.6, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Press militar", kcal_per_unit=0.5, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Curl de bíceps", kcal_per_unit=0.3, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Extensión de tríceps", kcal_per_unit=0.3, unit="repeticiones", is_predefined=True),
                    # HIIT / funcional
                    Exercise(user_id=None, name="Burpees", kcal_per_unit=0.8, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Mountain climbers", kcal_per_unit=0.3, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Jumping jacks", kcal_per_unit=0.2, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Box jumps", kcal_per_unit=0.7, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Kettlebell swing", kcal_per_unit=0.5, unit="repeticiones", is_predefined=True),
                    # Core
                    Exercise(user_id=None, name="Abdominales", kcal_per_unit=0.25, unit="repeticiones", is_predefined=True),
                    Exercise(user_id=None, name="Plancha", kcal_per_unit=3.5, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="Russian twist", kcal_per_unit=0.2, unit="repeticiones", is_predefined=True),
                    # Otros
                    Exercise(user_id=None, name="Yoga / Stretching", kcal_per_unit=3.0, unit="minutos", is_predefined=True),
                    Exercise(user_id=None, name="HIIT general", kcal_per_unit=13.0, unit="minutos", is_predefined=True),
                ]
                db.add_all(predefined_exercises)
                db.commit()

            db.close()
        return engine
    else:
        # Production: PostgreSQL
        return create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=40,
            connect_args={"client_encoding": "utf8"},
        )


engine = _get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
