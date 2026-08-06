"""Requêtes de la fiche amendement : détail, mentions, candidats à la similarité."""

from sqlalchemy import func, literal, select
from sqlalchemy.sql import Select

from models.acteur import Acteur
from models.amendement import Amendement
from models.amendement_mention import AmendementMention
from models.organe import Organe

#: Nombre de voisins retournés à l'UI, qui les filtre ensuite selon son seuil.
DEFAULT_SIMILAR_LIMIT = 8
#: Plafond de candidats scorés. Le scoring est vectoriel donc peu coûteux, mais
#: un article très chargé (9,4k amendements) n'a pas besoin d'être parcouru en
#: entier pour remonter huit voisins.
SIMILAR_CANDIDATE_LIMIT = 500


def amendement_detail(uid: str) -> Select:
    """Un amendement avec son auteur, sa circonscription et son groupe."""
    author = Acteur.__table__.alias("ac")
    circonscription = Organe.__table__.alias("oc")
    group = Organe.__table__.alias("og")

    return (
        select(
            Amendement.uid,
            Amendement.numeroLong,
            Amendement.numeroOrdreDepot,
            Amendement.dossierRefUid,
            Amendement.divisionArticleDesignation,
            Amendement.alineaDesignation,
            Amendement.sortAmendement,
            Amendement.dateDepot,
            Amendement.dateSort,
            Amendement.nombreCoSignataires,
            Amendement.scrutinRefUid,
            Amendement.groupePolitiqueRefUid,
            Amendement.codeEtape,
            Amendement.exposeSommaire,
            Amendement.dispositif,
            (author.c.civ + literal(" ") + author.c.nom).label("author_name"),
            author.c.civ,
            author.c.nom,
            author.c.prenom,
            func.coalesce(
                circonscription.c.libelleAbrev, circonscription.c.libelleEdition
            ).label("circonscription_label"),
            group.c.libelleAbrev.label("group_abbrev"),
            group.c.uid.label("group_uid"),
        )
        .select_from(Amendement)
        .outerjoin(author, author.c.uid == Amendement.acteurRefUid)
        .outerjoin(
            circonscription, circonscription.c.uid == author.c.circonscriptionUid
        )
        .outerjoin(group, group.c.uid == Amendement.groupePolitiqueRefUid)
        .where(Amendement.uid == uid)
    )


def amendement_similarity_keys(uid: str) -> Select:
    """Les seules colonnes dont `load_similars` a besoin pour bâtir sa requête."""
    return select(
        Amendement.uid,
        Amendement.dossierRefUid,
    ).where(Amendement.uid == uid)


def mentions_for_amendement(uid: str) -> Select:
    """Toutes les mentions détectées sur un amendement, dans l'ordre d'insertion."""
    return (
        select(AmendementMention)
        .where(AmendementMention.amendementUid == uid)
        .order_by(AmendementMention.id)
    )


def similar_candidates(
    dossier: str | None,
    uid: str,
    limit: int = SIMILAR_CANDIDATE_LIMIT,
) -> Select:
    """Candidats à la similarité : tout amendement d'un autre dossier législatif.

    L'article et le groupe politique ne sont plus des critères : deux
    amendements sur des sujets proches peuvent être portés par des dossiers,
    articles ou groupes différents. Seul le dossier lui-même est exclu, pour
    éviter de comparer un amendement à ses propres voisins de dossier.
    """
    candidate = Amendement.__table__.alias("a2")
    group = Organe.__table__.alias("og")
    author = Acteur.__table__.alias("ac")

    return (
        select(
            candidate.c.uid,
            candidate.c.numeroLong,
            candidate.c.sortAmendement,
            group.c.libelleAbrev.label("group_abbrev"),
            (author.c.civ + literal(" ") + author.c.nom).label("author_name"),
        )
        .select_from(candidate)
        .outerjoin(group, group.c.uid == candidate.c.groupePolitiqueRefUid)
        .outerjoin(author, author.c.uid == candidate.c.acteurRefUid)
        .where(
            candidate.c.dossierRefUid.is_distinct_from(dossier),
            candidate.c.uid != uid,
        )
        .order_by(candidate.c.numeroOrdreDepot.asc().nullslast())
        .limit(limit)
    )
