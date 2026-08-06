"""Accès Postgres en lecture pour l'API.

L'ETL crée son moteur avec `NullPool` : il fait quelques grosses transactions et
n'a rien à garder ouvert. Une API sert au contraire beaucoup de requêtes
courtes, d'où un moteur dédié avec un vrai pool, construit une seule fois et
partagé par toutes les requêtes.

Les helpers ci-dessous n'acceptent que des constructions SQLAlchemy
(`Executable`), jamais de chaîne SQL : les requêtes sont bâties dans
`api/queries/` avec `select()`, si bien qu'aucun fragment de SQL n'est assemblé
par concaténation de chaînes.
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.sql import Executable

from api.config import STATEMENT_TIMEOUT_MS, get_pool_size
from etl.database import get_db_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Moteur SQLAlchemy poolé, partagé par tout le processus."""
    return create_engine(
        get_db_url(),
        pool_size=get_pool_size(),
        max_overflow=0,
        pool_recycle=1800,
        # Une connexion coupée côté serveur (redémarrage, réseau) est détectée et
        # remplacée au checkout, au lieu de faire échouer la requête qui l'obtient.
        pool_pre_ping=True,
        connect_args={"options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}"},
    )


def dispose_engine() -> None:
    """Ferme le pool (arrêt de l'application)."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()


def fetch_all(statement: Executable) -> list[dict]:
    """Exécute `statement` et retourne les lignes en dictionnaires."""
    with get_engine().connect() as con:
        rows = con.execute(statement).mappings().all()
    return [dict(row) for row in rows]


def fetch_one(statement: Executable) -> dict | None:
    """Première ligne de `statement`, ou None si le résultat est vide."""
    with get_engine().connect() as con:
        row = con.execute(statement).mappings().first()
    return dict(row) if row is not None else None


def fetch_scalar(statement: Executable):
    """Première colonne de la première ligne, ou None."""
    with get_engine().connect() as con:
        return con.execute(statement).scalar()
