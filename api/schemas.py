"""Schémas de réponse de l'API.

Les noms de champs mélangent le camelCase issu du JSON source et le snake_case
issu des alias SQL : ils reprennent tels quels ceux de la base et des fichiers
d'origine, plutôt que d'imposer une normalisation qui masquerait la provenance.
`extra="allow"` sur les modèles qui exposent une ligne brute (`SELECT *`) évite
de dupliquer les ~60 colonnes de `scrutins`.

Ces schémas ne décrivent que les réponses de `/api/**` : les pages HTML de `web/`
consomment directement les dicts renvoyés par les fonctions de service.
"""

from pydantic import BaseModel, ConfigDict


class Stats(BaseModel):
    """Compteurs globaux du bandeau d'accueil."""

    dossier_count: int
    amendment_count: int
    mention_count: int
    scrutin_count: int


class DossierListItem(BaseModel):
    uid: str
    titre: str | None = None
    libelleProcedure: str | None = None
    statut: str | None = None
    dateDernierActe: str | None = None
    legislature: int | None = None
    amendment_count: int = 0
    mention_count: int = 0


class DossierList(BaseModel):
    dossiers: list[DossierListItem]
    total: int
    page: int
    limit: int


class Dossier(BaseModel):
    uid: str
    titre: str | None = None
    libelleProcedure: str | None = None
    codeProcedure: str | None = None
    statut: str | None = None
    dateDernierActe: str | None = None
    legislature: int | None = None


class DossierStats(BaseModel):
    amendment_count: int = 0
    adopted_count: int = 0
    group_count: int = 0
    scrutin_count: int = 0
    article_count: int = 0
    mention_count: int = 0


class HistogramBucket(BaseModel):
    """Un seau hebdomadaire de dépôts. `week` est une date 'YYYY-MM-DD'."""

    week: str
    cnt: int


class GroupCount(BaseModel):
    group_abbrev: str | None = None
    cnt: int


class LegislativeStep(BaseModel):
    """Une étape du parcours du texte, reconstituée depuis `actesLegislatifs`.

    Le nombre d'étapes varie d'un dossier à l'autre (une lecture unique en compte
    deux, la loi « fin de vie » dix) : la liste n'a pas de longueur fixe.
    """

    label: str
    date: str | None = None
    #: 'adopted' | 'rejected' | 'pending' | 'unknown'
    outcome: str = "unknown"
    #: Résultat abrégé pour l'affichage (« Texte adopté », « Désaccord »…).
    outcome_label: str = ""
    #: Libellé source complet de la conclusion, pour l'infobulle.
    detail: str = ""
    #: 'done' | 'current'
    state: str = "done"


class DossierDetail(BaseModel):
    dossier: Dossier
    stats: DossierStats
    histogram: list[HistogramBucket]
    mentionsByGroup: list[GroupCount]
    steps: list[LegislativeStep] = []


class Mention(BaseModel):
    """Mention de collaboration externe détectée dans un exposé sommaire."""

    model_config = ConfigDict(extra="allow")

    id: int
    citation: str | None = None
    formulation: str | None = None
    entite: str | None = None
    typeEntite: str | None = None
    externe: bool | None = None


class AmendementListItem(BaseModel):
    uid: str
    numeroLong: str | None = None
    divisionArticleDesignation: str | None = None
    alineaDesignation: str | None = None
    sortAmendement: str | None = None
    dateDepot: str | None = None
    nombreCoSignataires: int | None = None
    scrutinRefUid: str | None = None
    author_name: str | None = None
    group_abbrev: str | None = None
    similar_count: int = 0
    mentions: list[Mention] = []
    mention_count: int = 0
    mention_formulation: str | None = None
    mention_entite: str | None = None


class AmendementList(BaseModel):
    amendements: list[AmendementListItem]
    total: int
    totalWithMentions: int
    page: int
    limit: int


class Amendement(BaseModel):
    model_config = ConfigDict(extra="allow")

    uid: str
    numeroLong: str | None = None
    numeroOrdreDepot: int | None = None
    dossierRefUid: str | None = None
    divisionArticleDesignation: str | None = None
    alineaDesignation: str | None = None
    sortAmendement: str | None = None
    dateDepot: str | None = None
    dateSort: str | None = None
    nombreCoSignataires: int | None = None
    scrutinRefUid: str | None = None
    groupePolitiqueRefUid: str | None = None
    exposeSommaire: str | None = None
    dispositif: str | None = None
    codeEtape: str | None = None
    author_name: str | None = None
    civ: str | None = None
    nom: str | None = None
    prenom: str | None = None
    circonscription_label: str | None = None
    group_abbrev: str | None = None
    group_uid: str | None = None


class Similar(BaseModel):
    """Amendement proche. `score` est une similarité cosinus dans [0, 1]."""

    uid: str
    numeroLong: str | None = None
    sortAmendement: str | None = None
    group_abbrev: str | None = None
    author_name: str | None = None
    score: float


class Scrutin(BaseModel):
    model_config = ConfigDict(extra="allow")

    uid: str
    numero: str | None = None
    dateScrutin: str | None = None
    demandeur: str | None = None
    objet: str | None = None
    titre: str | None = None
    code: str | None = None
    libelle: str | None = None
    typeMajorite: str | None = None
    pour: int | None = None
    contre: int | None = None
    abstentions: int | None = None
    nonVotants: int | None = None
    nombreVotants: int | None = None
    suffragesExprimes: int | None = None


class GroupeVotant(BaseModel):
    model_config = ConfigDict(extra="allow")

    uid: str
    group_abbrev: str | None = None
    positionMajoritaire: str | None = None
    nombreMembresGroupe: int | None = None
    pour: int | None = None
    contre: int | None = None
    abstentions: int | None = None
    nonVotants: int | None = None
    #: Numéros de sièges (placeHemicycle) réellement occupés par le groupe à date,
    #: pour placer le vote sur le plan de l'hémicycle plutôt qu'un arc synthétique.
    sieges: list[str] = []


class AmendementDetail(BaseModel):
    amendement: Amendement
    mentions: list[Mention]
    scrutin: Scrutin | None = None
    groupesVotants: list[GroupeVotant] = []
    similars: list[Similar] = []
    #: False quand aucun embedding n'est disponible (`just embed` pas encore lancé) :
    #: l'UI peut alors distinguer « aucun amendement proche » de « scoring indisponible ».
    similarityAvailable: bool = True


class ScrutinDetail(BaseModel):
    scrutin: Scrutin
    groupesVotants: list[GroupeVotant]


class MentionFlowGroup(BaseModel):
    key: str
    label: str | None = None
    total: int


class MentionFlowSource(BaseModel):
    key: str
    label: str | None = None
    typeEntite: str | None = None
    total: int
    groupCount: int


class MentionFlowLink(BaseModel):
    group: str
    source: str
    value: int


class FormulationCount(BaseModel):
    label: str
    count: int


class DossierMentions(BaseModel):
    groups: list[MentionFlowGroup]
    sources: list[MentionFlowSource]
    links: list[MentionFlowLink]
    formulations: list[FormulationCount]
    #: Nombre de mentions détectées, toutes passes confondues (dont `gliner:v1`, qui
    #: nomme l'entité).
    detectedCount: int = 0
    #: Sous-ensemble portant une entité nommée : c'est la matière du diagramme.
    namedCount: int = 0
