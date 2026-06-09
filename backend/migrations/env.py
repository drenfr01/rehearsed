"""Alembic migration environment for the Rehearsed backend.

The schema for fresh databases is still created by
``SQLModel.metadata.create_all()`` at application startup; migrations exist to
evolve databases that already have tables. Migrations are therefore written
defensively (they no-op when the target table doesn't exist yet).
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

# Import all model modules so their tables register on SQLModel.metadata.
# This enables `alembic revision --autogenerate` to diff against the models.
from app.models import (  # noqa: F401
    agent,
    agent_llm_config,
    avatar,
    feedback,
    llm_model,
    scenario,
    session,
    thread,
    user,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _get_url() -> str:
    """Resolve the database URL for migrations.

    Order of precedence:
      1. ALEMBIC_DATABASE_URL (explicit override for migration runs)
      2. TEST_DATABASE_URL (matches the application's test behavior)
      3. The application's environment-based connection URL
    """
    url = os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if url:
        return url

    # Imported lazily: pulling in app settings requires a fully configured
    # environment (JWT secret, DB credentials, etc.).
    from app.services.database.base import get_connection_url

    return get_connection_url()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DB connection)."""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database."""
    connectable = create_engine(_get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
