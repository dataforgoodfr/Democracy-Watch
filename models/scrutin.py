from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Scrutin(Base):
    """Scrutin public (endpoint /scrutins) : un vote solennel de l'hémicycle sur un
    objet donné (amendement, article, ensemble d'un texte, motion…), avec le résultat
    agrégé (pour / contre / abstentions).

    Les références molles permettent de relier le scrutin à ce qui était voté :
    `dossierRefUid`, `documentRefUid`, `amendementRefUid`. Le détail par groupe est
    dans `groupesVotants`, le détail nominatif dans `votes`.
    """

    __tablename__ = "scrutins"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    legislature: Mapped[int | None]
    chambre: Mapped[str | None]
    numero: Mapped[str | None]
    dateScrutin: Mapped[str | None]
    demandeur: Mapped[str | None]

    # --- Objet voté ---
    objet: Mapped[str | None] = mapped_column(Text)
    titre: Mapped[str | None] = mapped_column(Text)
    typeObjet: Mapped[str | None]
    numeroTypeObjet: Mapped[str | None]

    # --- Type de scrutin / résultat ---
    codeTypeVote: Mapped[str | None]
    libelleTypeVote: Mapped[str | None]
    modePublicationDesVotes: Mapped[str | None]
    typeMajorite: Mapped[str | None]
    code: Mapped[str | None]
    libelle: Mapped[str | None]
    annonce: Mapped[str | None]

    # --- Décompte ---
    pour: Mapped[int | None]
    contre: Mapped[int | None]
    abstentions: Mapped[int | None]
    nonVotants: Mapped[int | None]
    nonVotantsVolontaires: Mapped[int | None]
    nombreVotants: Mapped[int | None]
    suffragesExprimes: Mapped[int | None]
    nbrSuffragesRequis: Mapped[int | None]

    # --- Rattachement (références molles indexées) ---
    organeRefUid: Mapped[str | None] = mapped_column(index=True)
    dossierRefUid: Mapped[str | None] = mapped_column(index=True)
    documentRefUid: Mapped[str | None] = mapped_column(index=True)
    amendementRefUid: Mapped[str | None] = mapped_column(index=True)
    articleRefUid: Mapped[str | None]
    seanceRefUid: Mapped[str | None]
    pointOdjRefUid: Mapped[str | None]
    acteLegislatifRefUid: Mapped[str | None]
    etapeLegislativeRefUid: Mapped[str | None]
    codeEtape: Mapped[str | None]
    quantiemeJourSeance: Mapped[str | None]

    # --- Dates ---
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
