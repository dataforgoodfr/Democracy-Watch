"""Compteurs globaux et sonde de disponibilité."""

from sqlalchemy import Integer, cast, func, literal, select
from sqlalchemy.sql import Select

from models.amendement import Amendement
from models.amendement_mention import AmendementMention
from models.dossier import Dossier
from models.scrutin import Scrutin

#: Législature couverte par le jeu de données chargé (voir queries/dossiers.py).
LEGISLATURE = 17


def _count_of(model, *conditions) -> Select:
    """Sous-requête scalaire comptant les lignes d'une table."""
    statement = select(cast(func.count(), Integer)).select_from(model)
    if conditions:
        statement = statement.where(*conditions)
    return statement.scalar_subquery()


def global_counts() -> Select:
    """Nombre de dossiers, amendements, mentions et scrutins en base.

    Les quatre sous-requêtes sont des agrégats : la ligne existe toujours.
    """
    return select(
        _count_of(Dossier, Dossier.legislature == LEGISLATURE).label("dossier_count"),
        _count_of(Amendement).label("amendment_count"),
        _count_of(AmendementMention).label("mention_count"),
        _count_of(Scrutin).label("scrutin_count"),
    )


def health_probe() -> Select:
    """Requête triviale confirmant que Postgres répond."""
    return select(literal(1).label("ok"))
