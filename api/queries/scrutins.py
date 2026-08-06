"""Requêtes des scrutins : fiche et vote agrégé par groupe."""

from sqlalchemy import ARRAY, String, cast, func, literal, select
from sqlalchemy.sql import Select

from models.groupe_votant import GroupeVotant
from models.mandat import Mandat
from models.organe import Organe
from models.scrutin import Scrutin

#: Législature couverte par le jeu de données chargé (voir queries/dossiers.py).
LEGISLATURE = 17


def scrutin_by_uid(uid: str) -> Select:
    """Un scrutin, toutes colonnes (le schéma en expose une soixantaine)."""
    return select(Scrutin).where(Scrutin.uid == uid)


def groupes_votants(scrutin_uid: str) -> Select:
    """Vote agrégé de chaque groupe, dans l'ordre de préséance.

    `sieges` remonte les numéros de siège (`placeHemicycle`) réellement occupés
    par le groupe à date : la sous-requête LATERAL relie le mandat de groupe (GP)
    au mandat d'assemblée du même acteur, seul porteur de la place.
    """
    mandat_groupe = Mandat.__table__.alias("mGroupe")
    mandat_assemblee = Mandat.__table__.alias("mAssemblee")

    sieges = (
        select(func.array_agg(mandat_assemblee.c.placeHemicycle).label("places"))
        .select_from(mandat_groupe)
        .join(
            mandat_assemblee,
            (mandat_assemblee.c.acteurRefUid == mandat_groupe.c.acteurRefUid)
            & (mandat_assemblee.c.legislature == LEGISLATURE)
            & (mandat_assemblee.c.typeOrgane == "ASSEMBLEE")
            & (mandat_assemblee.c.dateFin.is_(None))
            & (mandat_assemblee.c.placeHemicycle.is_not(None)),
        )
        .where(
            mandat_groupe.c.organeRefUid == GroupeVotant.organeRefUid,
            mandat_groupe.c.legislature == LEGISLATURE,
            mandat_groupe.c.typeOrgane == "GP",
            mandat_groupe.c.dateFin.is_(None),
        )
        .lateral("sieges")
    )

    return (
        select(
            GroupeVotant,
            Organe.libelleAbrev.label("group_abbrev"),
            Organe.uid.label("organe_uid"),
            Organe.preseance,
            Organe.poids,
            # `ARRAY[]::varchar[]` : un groupe sans siège renseigné doit remonter
            # un tableau vide, pas NULL, pour que l'UI itère sans test préalable.
            func.coalesce(
                sieges.c.places, cast(literal([], ARRAY(String)), ARRAY(String))
            ).label("sieges"),
        )
        .select_from(GroupeVotant)
        .join(Organe, Organe.uid == GroupeVotant.organeRefUid)
        .outerjoin(sieges, literal(True))
        .where(GroupeVotant.scrutinRefUid == scrutin_uid)
        .order_by(Organe.preseance.asc().nullslast())
    )
