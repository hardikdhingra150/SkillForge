from logging.config import fileConfig

from alembic import context
from sqlalchemy import text

from app.database import (
    audit_models,  # noqa: F401  (registers tables on Base.metadata)
    browser_models,  # noqa: F401  (registers tables on Base.metadata)
    chat_models,  # noqa: F401  (registers tables on Base.metadata)
    input_models,  # noqa: F401  (registers tables on Base.metadata)
    outcome_models,  # noqa: F401  (registers tables on Base.metadata)
    skill_models,  # noqa: F401  (registers tables on Base.metadata)
)
from app.database.connection import database_url, engine
from app.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# PostgreSQL 18 has uuidv7() built in. Older servers (Supabase runs 17) get the same function in SQL: a 48-bit
# millisecond timestamp, then random bits, with the version set to 7.
UUIDV7_FALLBACK = """
CREATE OR REPLACE FUNCTION public.uuidv7() RETURNS uuid LANGUAGE sql VOLATILE SET search_path = '' AS $$
  SELECT encode(set_bit(set_bit(overlay(uuid_send(gen_random_uuid())
    PLACING substring(int8send(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint) FROM 3)
    FROM 1 FOR 6), 52, 1), 53, 1), 'hex')::uuid
$$
"""


def ensure_uuidv7(connection):
    if connection.execute(text("SELECT current_setting('server_version_num')::int")).scalar() < 180000:
        connection.execute(text(UUIDV7_FALLBACK))


def run_migrations_online():
    with engine.connect() as connection:
        with connection.begin():
            ensure_uuidv7(connection)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()