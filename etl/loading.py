from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from etl.database import get_engine

# Nombre de lignes par INSERT. Le protocole Postgres plafonne à 65 535 paramètres
# par requête : avec ~40 colonnes, 1 000 lignes restent largement sous la limite.
# Indispensable pour les tables volumineuses (mandats, coSignatairesDocument…) qui
# dépasseraient sinon la limite en un seul INSERT.
BATCH_SIZE = 1000

# Colonnes ignorées pour décider si une ligne a changé. `dateMaj` est l'horodatage
# du lot d'export des tricoteuses, pas une date de modification de la ligne : sur
# 7 tables sur 9 il porte la même valeur pour toutes les lignes et change à chaque
# téléchargement. Le comparer reviendrait à réécrire l'intégralité de ces tables à
# chaque exécution.
IGNORED_FOR_COMPARISON = {"dateMaj"}


def _get_primary_key(table):
    return [column.name for column in table.primary_key.columns]


def _deduplicate(table, data):
    """Ne garder qu'une ligne par clé primaire.

    La pagination de l'API sert parfois deux fois la même entrée (~640 doublons
    sur organes, ~77 sur scrutins). Postgres interdit qu'un ON CONFLICT DO UPDATE
    touche deux fois la même ligne dans une seule commande : sans déduplication,
    l'INSERT échoue.
    """
    keys = _get_primary_key(table)
    unique = {tuple(row[key] for key in keys): row for row in data}
    return list(unique.values())


def _upsert(table, batch):
    """INSERT ... ON CONFLICT DO UPDATE n'écrivant que les lignes réellement modifiées.

    Le WHERE compare la ligne existante à celle proposée : sans lui, chaque
    exécution réécrirait toutes les lignes. Or un UPDATE Postgres n'est jamais
    fait sur place (nouvelle version du tuple, index et WAL mis à jour), ce qui
    ferait gonfler la base pour rien.
    """
    statement = insert(table).values(batch)
    keys = _get_primary_key(table)
    updatable = [column.name for column in table.columns if column.name not in keys]
    compared = [name for name in updatable if name not in IGNORED_FOR_COMPARISON]
    return statement.on_conflict_do_update(
        index_elements=keys,
        set_={name: statement.excluded[name] for name in updatable},
        where=tuple_(*(table.c[name] for name in compared)).is_distinct_from(
            tuple_(*(statement.excluded[name] for name in compared))
        ),
    )


def load(table, data):
    """Load into the database the data for the given fields, in batches."""
    data = _deduplicate(table, data)
    with Session(get_engine()) as session:
        for start in range(0, len(data), BATCH_SIZE):
            session.execute(_upsert(table, data[start : start + BATCH_SIZE]))
        session.commit()
