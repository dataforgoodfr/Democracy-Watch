from os import getenv

from sqlalchemy import URL, create_engine, pool

import models  # noqa: F401  # pyright: ignore[reportUnusedImport]  # registers all ORM models with Base.metadata
from models.base import Base


def _get_db_url():
    PG_USER = getenv("PG_USER")
    PG_PWD = getenv("PG_PWD")
    PG_DB = getenv("PG_DB")
    PG_HOST = getenv("PG_HOST", "localhost")
    PG_PORT = getenv("PG_PORT", "5432")
    return URL.create(
        drivername="postgresql+psycopg",
        username=PG_USER,
        password=PG_PWD,
        host=PG_HOST,
        port=int(PG_PORT),
        database=PG_DB,
    )


def get_engine():
    """Return a configured SQLAlchemy engine"""
    PG_ECHO = getenv("PG_ECHO", False)
    pg_url = _get_db_url()
    return create_engine(pg_url, poolclass=pool.NullPool, echo=bool(PG_ECHO))


def create_db():
    """Drop the current DB and recreate from the schema."""
    print("Creating DB")
    engine = get_engine()
    print(Base.metadata.tables)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Db was created")
    return Base.metadata.tables


def get_tables_definition():
    return Base.metadata.sorted_tables
