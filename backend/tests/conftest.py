"""Test fixtures.

Each test gets its own throwaway SQLite file and its own session, injected over
get_db — deliberately *not* the demo database in %TEMP%, which is shared, seeded
and only deleted on a best-effort basis.
"""
import os

# Must be set before app.config is imported, or the engine tries to reach Postgres.
os.environ.setdefault("DEMO_MODE", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.limiter import limiter
from app.main import app
from app.models import User
from app.security import create_access_token, hash_password

API = "/api"


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):  # SQLite needs asking, unlike Postgres
        dbapi_conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _no_rate_limits():
    """Los límites van por IP y el TestClient es siempre la misma.

    Sin esto, el 10/hour de POST /friends se agota a mitad de la suite y los
    tests que vienen después fallan por el orden en que se ejecutan, no por lo
    que comprueban. Los límites se prueban aparte, no de refilón.
    """
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture()
def client(db):
    def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db):
    def _make(name: str) -> User:
        user = User(
            email=f"{name.lower()}@example.com",
            password_hash=hash_password("irrelevant"),
            name=name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def make_product(db):
    from app.models import Product
    from app.models.product import ProductSource

    def _make(name: str = "Arroz") -> Product:
        product = Product(
            name=name,
            calories_per_100g=350,
            protein_per_100g=7,
            carbs_per_100g=77,
            fat_per_100g=1,
            source=ProductSource.manual,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    return _make


def auth(user: User) -> dict[str, str]:
    """Headers for a real signed token — no shortcut around the auth dependency."""
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}
