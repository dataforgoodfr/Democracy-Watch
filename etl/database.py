from os import getenv

from sqlalchemy import URL, create_engine, pool

import models  # noqa: F401  # pyright: ignore[reportUnusedImport]  # registers all ORM models with Base.metadata
from models.base import Base

# Tables alimentées par l'ETL depuis les fichiers JSON de ./data.
# Seules ces tables sont détruites lors d'un rebuild et parcourues par l'ETL.
# Les tables d'analyse (ajoutées plus tard) en sont volontairement exclues afin
# que leurs résultats survivent à un rebuild et ne soient pas traitées comme des
# fichiers source à charger.
ETL_TABLES = {
    "dossiers",
    "amendements",
    # Objets ajoutés pour les recoupements auteur / groupe / texte / vote agrégé.
    "acteurs",
    "organes",
    "mandats",
    "scrutins",
    "groupesVotants",
    "documents",
    "auteursDocument",
    "coSignatairesDocument",
}


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
    # getenv renvoie une chaîne : bool("False") vaudrait True, d'où la comparaison explicite.
    pg_echo = getenv("PG_ECHO", "").strip().lower() == "true"
    pg_url = _get_db_url()
    return create_engine(pg_url, poolclass=pool.NullPool, echo=pg_echo)


def _get_etl_tables():
    """Return the schema definitions of the ETL-managed tables only."""
    return [table for table in Base.metadata.sorted_tables if table.name in ETL_TABLES]


def create_db():
    """Rebuild the ETL-managed tables from the schema.

    Only the tables listed in ETL_TABLES are dropped and recreated. Analysis
    tables are left untouched so their results survive a rebuild; create_all is
    idempotent and (re)creates any missing table without altering existing ones.
    """
    print("Creating DB")
    engine = get_engine()
    etl_tables = _get_etl_tables()
    print(etl_tables)
    Base.metadata.drop_all(engine, tables=etl_tables)
    Base.metadata.create_all(engine)
    print("Db was created")
    return Base.metadata.tables


def get_tables_definition():
    return _get_etl_tables()
