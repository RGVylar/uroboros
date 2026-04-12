from logging.config import fileConfig
import os

# Set migration flag before importing app modules
os.environ["ALEMBIC_MIGRATION"] = "true"

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app import models  # noqa: F401  (register models on Base.metadata)

config = context.config

# Use SQLite for demo mode migrations, PostgreSQL otherwise
if settings.demo_mode or os.getenv("DEMO_MODE", "").lower() == "true":
    import tempfile
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, "uroboros_demo.db")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
else:
    config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    connect_args = {}
    url = config.get_main_option("sqlalchemy.url", "")
    if url.startswith("postgresql"):
        connect_args["client_encoding"] = "utf8"

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
