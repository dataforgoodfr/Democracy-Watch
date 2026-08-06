"""Requêtes des dossiers : liste, fiche, amendements, mentions."""

from sqlalchemy import (
    TIMESTAMP,
    Integer,
    and_,
    cast,
    distinct,
    exists,
    func,
    literal,
    select,
)
from sqlalchemy.dialects.postgresql import JSON, aggregate_order_by
from sqlalchemy.sql import ColumnElement, Select

from models.acte_legislatif import ActeLegislatif
from models.acteur import Acteur
from models.amendement import Amendement
from models.amendement_mention import AmendementMention
from models.dossier import Dossier
from models.organe import Organe

#: Législature couverte par le jeu de données chargé.
LEGISLATURE = 17

DOSSIERS_PAGE_SIZE = 10
AMENDEMENTS_MAX_PAGE_SIZE = 100


# --- Liste des dossiers ---------------------------------------------------------


def _dossier_filters(
    q: str = "",
    procedure: str | None = None,
    statut: str | None = None,
    with_mentions: bool = False,
) -> list[ColumnElement[bool]]:
    """Conditions de la liste des dossiers, partagées par la page et son total.

    Renvoyer une liste de conditions (et non un fragment de SQL) garantit que la
    requête de comptage porte exactement le même prédicat que celle de la page :
    le total colle donc toujours au jeu de lignes affiché.
    """
    conditions: list[ColumnElement[bool]] = [Dossier.legislature == LEGISLATURE]

    if procedure:
        conditions.append(Dossier.codeProcedure == procedure)
    if statut:
        conditions.append(Dossier.statut == statut)
    if with_mentions:
        conditions.append(
            exists(
                select(literal(1))
                .select_from(AmendementMention)
                .join(Amendement, Amendement.uid == AmendementMention.amendementUid)
                .where(Amendement.dossierRefUid == Dossier.uid)
            )
        )
    if q:
        # `ilike` lie le motif en paramètre : les `%` encadrants ne sont pas
        # concaténés dans le SQL mais passés comme valeur.
        pattern = f"%{q}%"
        conditions.append(Dossier.titre.ilike(pattern) | Dossier.uid.ilike(pattern))

    return conditions


def dossiers_page(
    q: str = "",
    page: int = 1,
    procedure: str | None = None,
    statut: str | None = None,
    with_mentions: bool = False,
    limit: int = DOSSIERS_PAGE_SIZE,
) -> Select:
    """Une page de dossiers, avec le nombre d'amendements et de mentions.

    Les compteurs viennent de sous-requêtes LATERAL corrélées et non de LEFT JOIN
    empilés : joindre amendements *et* amendement_mentions produirait
    (amendements x mentions) lignes par dossier, ce que COUNT(DISTINCT ...)
    masquerait mais qui rendrait le parcours quadratique.
    """
    amendment_count = (
        select(cast(func.count(), Integer).label("amendment_count"))
        .select_from(Amendement)
        .where(Amendement.dossierRefUid == Dossier.uid)
        .lateral("ac")
    )
    mention_count = (
        select(cast(func.count(), Integer).label("mention_count"))
        .select_from(AmendementMention)
        .join(Amendement, Amendement.uid == AmendementMention.amendementUid)
        .where(Amendement.dossierRefUid == Dossier.uid)
        .lateral("mc")
    )

    return (
        select(
            Dossier.uid,
            Dossier.titre,
            Dossier.libelleProcedure,
            Dossier.statut,
            Dossier.dateDernierActe,
            Dossier.legislature,
            func.coalesce(amendment_count.c.amendment_count, 0).label(
                "amendment_count"
            ),
            func.coalesce(mention_count.c.mention_count, 0).label("mention_count"),
        )
        .select_from(Dossier)
        .outerjoin(amendment_count, literal(True))
        .outerjoin(mention_count, literal(True))
        .where(and_(*_dossier_filters(q, procedure, statut, with_mentions)))
        .order_by(Dossier.dateDernierActe.desc().nullslast(), Dossier.uid)
        .limit(limit)
        .offset((page - 1) * limit)
    )


def dossiers_count(
    q: str = "",
    procedure: str | None = None,
    statut: str | None = None,
    with_mentions: bool = False,
) -> Select:
    """Total de la liste des dossiers, sous le même prédicat que `dossiers_page`."""
    return (
        select(cast(func.count(), Integer).label("total"))
        .select_from(Dossier)
        .where(and_(*_dossier_filters(q, procedure, statut, with_mentions)))
    )


# --- Fiche dossier --------------------------------------------------------------


def dossier_by_uid(uid: str) -> Select:
    """Métadonnées d'un dossier."""
    return select(
        Dossier.uid,
        Dossier.titre,
        Dossier.libelleProcedure,
        Dossier.codeProcedure,
        Dossier.statut,
        Dossier.dateDernierActe,
        Dossier.legislature,
    ).where(Dossier.uid == uid)


def dossier_actes(uid: str) -> Select:
    """Tous les actes de la procédure d'un dossier.

    L'arbre entier est remonté (et non les seules racines) : le sort d'une étape
    n'est porté que par son acte de décision, quelque part dans ses descendants.
    Un dossier en compte au plus quelques centaines, la reconstitution se fait
    donc en Python (`web/legislative.py`) plutôt qu'en SQL récursif.
    """
    return (
        select(
            ActeLegislatif.uid,
            ActeLegislatif.parentUid,
            ActeLegislatif.codeActe,
            ActeLegislatif.nomCanonique,
            ActeLegislatif.libelleCourtActe,
            ActeLegislatif.xsiType,
            ActeLegislatif.chambre,
            ActeLegislatif.dateActe,
            ActeLegislatif.libelleStatutConclusion,
            ActeLegislatif.libelleDecision,
        )
        .where(ActeLegislatif.dossierRefUid == uid)
        .order_by(ActeLegislatif.dateActe.asc().nullsfirst(), ActeLegislatif.uid)
    )


def dossier_stats(uid: str) -> Select:
    """Compteurs d'un dossier.

    `mention_count` est une sous-requête scalaire et non un LEFT JOIN, pour que
    les lignes d'amendements ne soient pas multipliées par leurs mentions
    (jusqu'à 8 par amendement).
    """
    # `amendements` est aliasé : la requête englobante sélectionne déjà cette
    # table, et sans alias l'auto-corrélation de SQLAlchemy pourrait la retirer
    # du FROM interne et changer le sens de la sous-requête.
    inner = Amendement.__table__.alias("a2")
    mention_count = (
        select(cast(func.count(), Integer))
        .select_from(AmendementMention)
        .join(inner, inner.c.uid == AmendementMention.amendementUid)
        .where(inner.c.dossierRefUid == uid)
        .scalar_subquery()
    )

    return (
        select(
            cast(func.count(), Integer).label("amendment_count"),
            cast(
                func.count().filter(Amendement.sortAmendement.ilike("adopt%")), Integer
            ).label("adopted_count"),
            cast(
                func.count(func.distinct(Amendement.groupePolitiqueRefUid)), Integer
            ).label("group_count"),
            cast(func.count(func.distinct(Amendement.scrutinRefUid)), Integer).label(
                "scrutin_count"
            ),
            cast(
                func.count(func.distinct(Amendement.divisionArticleDesignation)),
                Integer,
            ).label("article_count"),
            mention_count.label("mention_count"),
        )
        .select_from(Amendement)
        .where(Amendement.dossierRefUid == uid)
    )


def dossier_histogram(uid: str) -> Select:
    """Dépôts d'amendements par semaine.

    `dateDepot` est une chaîne ISO-8601 complète ("2026-05-06T00:00:00.000Z"). On
    la lit comme timestamptz (et non via TO_DATE, qui ignore le décalage) et on
    renvoie le seau comme *chaîne* 'YYYY-MM-DD' : un `timestamp` nu serait relu
    en heure locale par le client, décalant chaque seau d'un jour.
    """
    week = func.to_char(
        func.date_trunc(
            "week",
            # `AT TIME ZONE 'UTC'` en SQL ; le cast timestamptz honore le décalage
            # présent dans la chaîne, ce que TO_DATE ignorerait.
            func.timezone(
                "UTC", cast(Amendement.dateDepot, TIMESTAMP(timezone=True))
            ),
        ),
        "YYYY-MM-DD",
    ).label("week")

    return (
        select(week, cast(func.count(), Integer).label("cnt"))
        .select_from(Amendement)
        .where(
            Amendement.dossierRefUid == uid,
            Amendement.dateDepot.is_not(None),
        )
        .group_by(week)
        .order_by(week)
    )


def dossier_mentions_by_group(uid: str) -> Select:
    """Mentions externes d'un dossier, ventilées par groupe politique."""
    cnt = cast(func.count(AmendementMention.id), Integer).label("cnt")

    return (
        select(Organe.libelleAbrev.label("group_abbrev"), cnt)
        .select_from(AmendementMention)
        .join(Amendement, Amendement.uid == AmendementMention.amendementUid)
        .join(Organe, Organe.uid == Amendement.groupePolitiqueRefUid)
        .where(
            Amendement.dossierRefUid == uid,
            AmendementMention.externe.is_(True),
        )
        .group_by(Organe.libelleAbrev)
        .order_by(cnt.desc())
    )


# --- Amendements d'un dossier ---------------------------------------------------

#: Tris exposés à l'UI. `relevance` (défaut) retombe sur la date de dépôt : il
#: n'y a pas de score de pertinence sur cette liste.
ORDER_CLAUSES = {
    "date": (Amendement.dateDepot.desc().nullslast(), Amendement.uid),
    "numero": (Amendement.numeroOrdreDepot.asc().nullslast(), Amendement.uid),
    "relevance": (Amendement.dateDepot.desc().nullslast(), Amendement.uid),
}


def amendements_page(
    uid: str,
    q: str = "",
    page: int = 1,
    limit: int = 10,
    sort: str = "relevance",
    article: str | None = None,
    groupe: str | None = None,
    sort_filter: str | None = None,
    with_mentions: bool = False,
) -> Select:
    """Une page d'amendements d'un dossier, avec auteur, groupe et mentions.

    `article_counts` remplace une auto-jointure qui explosait en ~n² lignes par
    article (l'article 49 d'un dossier porte 9,4k amendements => ~88M lignes =>
    statement timeout). Compter une fois par article est en O(n), et le -1 exclut
    la ligne elle-même.
    """
    article_counts = (
        select(
            Amendement.divisionArticleDesignation.label("article"),
            func.count().label("n"),
        )
        .where(Amendement.dossierRefUid == uid)
        .group_by(Amendement.divisionArticleDesignation)
        .cte("article_counts")
    )

    # Agrégé en LATERAL pour qu'un amendement à plusieurs mentions reste UNE
    # ligne : joindre amendement_mentions directement dupliquerait les lignes
    # (jusqu'à 8x) et désynchroniserait la pagination.
    mention_object = func.json_build_object(
        "id",
        AmendementMention.id,
        "formulation",
        AmendementMention.formulation,
        "entite",
        AmendementMention.entite,
        "typeEntite",
        AmendementMention.typeEntite,
        "externe",
        AmendementMention.externe,
    )
    mentions = (
        select(
            func.json_agg(
                aggregate_order_by(mention_object, AmendementMention.id)
            ).label("mentions"),
            func.count().label("mention_count"),
            func.array_agg(
                aggregate_order_by(AmendementMention.formulation, AmendementMention.id)
            )[1].label("formulation"),
            func.array_agg(
                aggregate_order_by(AmendementMention.entite, AmendementMention.id)
            )[1].label("entite"),
        )
        .select_from(AmendementMention)
        .where(AmendementMention.amendementUid == Amendement.uid)
        .lateral("mn")
    )

    author = Acteur.__table__.alias("ac")
    group = Organe.__table__.alias("og")

    order_by = ORDER_CLAUSES.get(sort, ORDER_CLAUSES["relevance"])

    return (
        select(
            Amendement.uid,
            Amendement.numeroLong,
            Amendement.divisionArticleDesignation,
            Amendement.alineaDesignation,
            Amendement.sortAmendement,
            Amendement.dateDepot,
            Amendement.nombreCoSignataires,
            Amendement.scrutinRefUid,
            (author.c.civ + literal(" ") + author.c.nom).label("author_name"),
            group.c.libelleAbrev.label("group_abbrev"),
            cast(
                func.greatest(func.coalesce(article_counts.c.n, 1) - 1, 0), Integer
            ).label("similar_count"),
            func.coalesce(mentions.c.mentions, cast(literal("[]"), JSON)).label(
                "mentions"
            ),
            cast(func.coalesce(mentions.c.mention_count, 0), Integer).label(
                "mention_count"
            ),
            mentions.c.formulation.label("mention_formulation"),
            mentions.c.entite.label("mention_entite"),
        )
        .select_from(Amendement)
        .outerjoin(author, author.c.uid == Amendement.acteurRefUid)
        .outerjoin(group, group.c.uid == Amendement.groupePolitiqueRefUid)
        .outerjoin(
            article_counts,
            article_counts.c.article.is_not_distinct_from(
                Amendement.divisionArticleDesignation
            ),
        )
        .outerjoin(mentions, literal(True))
        .where(
            and_(
                *_amendement_filters(
                    uid, q, article, groupe, sort_filter, with_mentions, group
                )
            )
        )
        .order_by(*order_by)
        .limit(limit)
        .offset((page - 1) * limit)
    )


def _amendement_filters(
    uid: str,
    q: str,
    article: str | None,
    groupe: str | None,
    sort_filter: str | None,
    with_mentions: bool,
    group_alias,
) -> list[ColumnElement[bool]]:
    """Conditions de la liste d'amendements, partagées par la page et son total.

    Le filtre groupe porte sur `group_alias` : la page et le comptage joignent
    `organes` sous un alias distinct, et le filtre doit référencer celui de la
    requête courante sous peine de produire une jointure cartésienne implicite.
    """
    conditions: list[ColumnElement[bool]] = [Amendement.dossierRefUid == uid]

    if article:
        conditions.append(Amendement.divisionArticleDesignation.ilike(f"%{article}%"))
    if groupe:
        conditions.append(group_alias.c.libelleAbrev == groupe)
    if sort_filter:
        conditions.append(Amendement.sortAmendement.ilike(f"%{sort_filter}%"))
    if with_mentions:
        conditions.append(
            exists(
                select(literal(1))
                .select_from(AmendementMention)
                .where(AmendementMention.amendementUid == Amendement.uid)
            )
        )
    if q:
        pattern = f"%{q}%"
        conditions.append(
            Amendement.exposeSommaire.ilike(pattern)
            | Amendement.dispositif.ilike(pattern)
            | Amendement.numeroLong.ilike(pattern)
        )

    return conditions


def amendements_facets(uid: str) -> Select:
    """Valeurs distinctes des facettes disponibles pour les amendements d'un dossier."""
    group = Organe.__table__.alias("og")

    # Sous-requêtes séparées pour chaque facette, car array_agg ne peut pas contenir
    # plusieurs DISTINCT sur des colonnes différentes dans une seule requête.
    articles_cte = (
        select(func.array_agg(distinct(Amendement.divisionArticleDesignation)).label("articles"))
        .select_from(Amendement)
        .where(
            Amendement.dossierRefUid == uid,
            Amendement.divisionArticleDesignation.is_not(None),
        )
        .scalar_subquery()
    )

    groupes_cte = (
        select(func.array_agg(distinct(group.c.libelleAbrev)).label("groupes"))
        .select_from(Amendement)
        .outerjoin(group, group.c.uid == Amendement.groupePolitiqueRefUid)
        .where(
            Amendement.dossierRefUid == uid,
            group.c.libelleAbrev.is_not(None),
        )
        .scalar_subquery()
    )

    sorts_cte = (
        select(func.array_agg(distinct(Amendement.sortAmendement)).label("sorts"))
        .select_from(Amendement)
        .where(
            Amendement.dossierRefUid == uid,
            Amendement.sortAmendement.is_not(None),
        )
        .scalar_subquery()
    )

    return select(
        articles_cte.label("articles"),
        groupes_cte.label("groupes"),
        sorts_cte.label("sorts"),
    )


def amendements_count(
    uid: str,
    q: str = "",
    article: str | None = None,
    groupe: str | None = None,
    sort_filter: str | None = None,
    with_mentions: bool = False,
) -> Select:
    """Total de la liste d'amendements, mêmes prédicats et jointures que la page."""
    group = Organe.__table__.alias("og")

    return (
        select(cast(func.count(), Integer).label("total"))
        .select_from(Amendement)
        .outerjoin(group, group.c.uid == Amendement.groupePolitiqueRefUid)
        .where(
            and_(
                *_amendement_filters(
                    uid, q, article, groupe, sort_filter, with_mentions, group
                )
            )
        )
    )


def amendements_with_mentions_count(uid: str) -> Select:
    """Nombre d'amendements du dossier portant au moins une mention détectée."""
    return (
        select(cast(func.count(), Integer).label("total"))
        .select_from(Amendement)
        .where(
            Amendement.dossierRefUid == uid,
            exists(
                select(literal(1))
                .select_from(AmendementMention)
                .where(AmendementMention.amendementUid == Amendement.uid)
            ),
        )
    )


# --- Mentions d'un dossier ------------------------------------------------------


def mention_counts(uid: str) -> Select:
    """Mentions détectées et mentions nommées d'un dossier.

    Le diagramme de flux a besoin d'une entité *nommée*, que seule la passe
    d'enrichissement LLM produit (`modele` = llm:*). La passe gliner (`gliner:v1`)
    détecte la formulation de collaboration mais laisse entite/typeEntite/externe
    à NULL, et elle couvre beaucoup plus d'amendements. Remonter les deux
    compteurs évite d'annoncer « 0 mention » sur un dossier qui en a des
    centaines, simplement en attente d'enrichissement.
    """
    return (
        select(
            cast(func.count(), Integer).label("detected"),
            cast(
                func.count().filter(
                    AmendementMention.externe.is_(True),
                    AmendementMention.entite.is_not(None),
                ),
                Integer,
            ).label("named"),
        )
        .select_from(AmendementMention)
        .join(Amendement, Amendement.uid == AmendementMention.amendementUid)
        .where(Amendement.dossierRefUid == uid)
    )


def mention_links(uid: str) -> Select:
    """Une ligne par (groupe, entité, type, formulation), pour le diagramme."""
    value = cast(func.count(), Integer).label("value")

    return (
        select(
            Organe.libelleAbrev.label("group_key"),
            Organe.libelleAbrev.label("group_label"),
            AmendementMention.entite.label("source_key"),
            AmendementMention.entite.label("source_label"),
            AmendementMention.typeEntite.label("type_entite"),
            AmendementMention.formulation,
            value,
        )
        .select_from(AmendementMention)
        .join(Amendement, Amendement.uid == AmendementMention.amendementUid)
        .join(Organe, Organe.uid == Amendement.groupePolitiqueRefUid)
        .where(
            Amendement.dossierRefUid == uid,
            AmendementMention.externe.is_(True),
            AmendementMention.entite.is_not(None),
        )
        .group_by(
            Organe.libelleAbrev,
            AmendementMention.entite,
            AmendementMention.typeEntite,
            AmendementMention.formulation,
        )
        .order_by(value.desc())
    )


__all__ = [
    "AMENDEMENTS_MAX_PAGE_SIZE",
    "DOSSIERS_PAGE_SIZE",
    "LEGISLATURE",
    "ORDER_CLAUSES",
    "amendements_count",
    "amendements_facets",
    "amendements_page",
    "amendements_with_mentions_count",
    "dossier_actes",
    "dossier_by_uid",
    "dossier_histogram",
    "dossier_mentions_by_group",
    "dossier_stats",
    "dossiers_count",
    "dossiers_page",
    "mention_counts",
    "mention_links",
]
