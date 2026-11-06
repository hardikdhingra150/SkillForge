from sqlalchemy import URL, create_engine, make_url

from app.config import settings


def build_url() -> URL:
    """DATABASE_URL (e.g. Supabase) when set, else the POSTGRES_* values. Always the psycopg 3 driver."""
    if settings.database_url is not None:
        url = make_url(settings.database_url.get_secret_value()).set(drivername="postgresql+psycopg")
        # Hosted databases (Supabase included) need TLS; local ones don't support it.
        if url.host not in (None, "localhost", "127.0.0.1", "postgres") and "sslmode" not in url.query:
            url = url.update_query_dict({"sslmode": "require"})
        return url
    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


database_url = build_url()

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_timeout=5,
    connect_args={"connect_timeout": 10},
    hide_parameters=True,
)
