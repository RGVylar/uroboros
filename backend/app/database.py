from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _get_engine():
    if settings.demo_mode:
        # SQLite in-memory for demo/preview
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create all tables
        Base.metadata.create_all(engine)

        # Seed demo data
        from app.models import Product, User
        from app.models.product import ProductSource
        from app.security import hash_password

        db = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

        # Create demo users
        user1 = User(email="demo@demo.com", hashed_password=hash_password("demo123"), name="Demo User")
        user2 = User(email="demo2@demo.com", hashed_password=hash_password("demo123"), name="Demo 2")
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

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
        ]
        db.add_all(demo_products)
        db.commit()

        db.close()
        return engine
    else:
        # Production: PostgreSQL
        return create_engine(
            settings.database_url,
            pool_pre_ping=True,
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
