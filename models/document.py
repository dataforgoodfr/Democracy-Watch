from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Document(Base):
    """Document parlementaire (endpoint /documents) : les textes eux-mêmes — projets
    et propositions de loi, rapports, accords internationaux…

    Se rattache au dossier législatif par `dossierRefUid` et porte l'auteur principal
    (`auteurPrincipalUid`). L'exposé des motifs (`exposeMotifsTexte`) est l'équivalent,
    côté texte, de l'exposé sommaire d'un amendement.
    """

    __tablename__ = "documents"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    legislature: Mapped[int | None]
    chambre: Mapped[str | None]
    numNotice: Mapped[str | None]
    texteLoi: Mapped[bool | None]
    amendable: Mapped[bool | None]
    estDisponible: Mapped[bool | None]
    adoptionConforme: Mapped[bool | None]

    # --- Titres / contenu ---
    titrePrincipal: Mapped[str | None] = mapped_column(Text)
    titrePrincipalCourt: Mapped[str | None] = mapped_column(Text)
    formule: Mapped[str | None] = mapped_column(Text)
    exposeMotifsTexte: Mapped[str | None] = mapped_column(Text)
    exposeMotifsHtml: Mapped[str | None] = mapped_column(Text)
    denominationStructurelle: Mapped[str | None]

    # --- Classification ---
    classeCode: Mapped[str | None]
    classeLibelle: Mapped[str | None]
    typeCode: Mapped[str | None]
    typeLibelle: Mapped[str | None]
    sousTypeCode: Mapped[str | None]
    sousTypeLibelle: Mapped[str | None]
    sousTypeLibelleEdition: Mapped[str | None]
    especeCode: Mapped[str | None]
    especeLibelle: Mapped[str | None]
    depotCode: Mapped[str | None]
    depotLibelle: Mapped[str | None]
    provenance: Mapped[str | None]
    statutAdoption: Mapped[str | None]
    niveauCorrection: Mapped[str | None]
    typeCorrection: Mapped[str | None]
    xsiType: Mapped[str | None]

    # --- Rattachement (références molles indexées) ---
    dossierRefUid: Mapped[str | None] = mapped_column(index=True)
    documentParentRefUid: Mapped[str | None] = mapped_column(index=True)
    auteurPrincipalUid: Mapped[str | None] = mapped_column(index=True)
    organeRefUid: Mapped[str | None] = mapped_column(index=True)
    etapeLegislativePrincipaleRefUid: Mapped[str | None]

    # --- Divers ---
    nbPage: Mapped[str | None]
    prix: Mapped[str | None]
    isbn: Mapped[str | None]
    pdfUrl: Mapped[str | None]

    # --- Dates ---
    dateCreation: Mapped[str | None]
    dateDepot: Mapped[str | None]
    datePublication: Mapped[str | None]
    datePublicationWeb: Mapped[str | None]
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
