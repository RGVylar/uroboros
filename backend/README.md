# Uroboros Backend

FastAPI + SQLAlchemy + Alembic + PostgreSQL.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
cp .env.example .env
```

## Migrations

```bash
alembic upgrade head
# autogenerate a new revision after editing models:
alembic revision --autogenerate -m "message"
```

## Run

```bash
uvicorn app.main:app --reload
```
