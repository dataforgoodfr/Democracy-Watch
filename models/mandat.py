from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Mandat(Base):
    """Mandat parlementaire (endpoint /mandats) : table de jointure entre un acteur
    et un organe (appartenance à un groupe, une commission, une délégation…), avec
    la qualité occupée et les dates de début/fin.

    C'est le pivot pour rattacher un acteur à son groupe politique à une date donnée
    (`acteurRefUid` → acteurs, `organeRefUid` → organes).
    """

    __tablename__ = "mandats"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    legislature: Mapped[int | None]
    chambre: Mapped[str | None]
    typeOrgane: Mapped[str | None]
    xsiType: Mapped[str | None]
    actif: Mapped[bool | None]
    nominPrincipale: Mapped[bool | None]

    # --- Rattachement (références molles indexées pour les jointures) ---
    acteurRefUid: Mapped[str | None] = mapped_column(index=True)
    organeRefUid: Mapped[str | None] = mapped_column(index=True)
    mandatRemplaceRefUid: Mapped[str | None]
    missionPrecedenteRefUid: Mapped[str | None]

    # --- Qualité ---
    codeQualite: Mapped[str | None]
    libQualite: Mapped[str | None]
    libQualiteSex: Mapped[str | None]
    libelle: Mapped[str | None]
    causeMandat: Mapped[str | None]
    causeFin: Mapped[str | None]

    # --- Circonscription / territoire ---
    refCirconscription: Mapped[str | None]
    region: Mapped[str | None]
    regionType: Mapped[str | None]
    departement: Mapped[str | None]
    numDepartement: Mapped[int | None]
    numCirco: Mapped[int | None]
    placeHemicycle: Mapped[str | None]
    preseance: Mapped[int | None]
    premiereElection: Mapped[str | None]

    # --- Dates ---
    dateDebut: Mapped[str | None]
    dateFin: Mapped[str | None]
    datePriseFonction: Mapped[str | None]
    datePublication: Mapped[str | None]
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
