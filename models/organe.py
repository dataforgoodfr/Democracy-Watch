from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Organe(Base):
    """Organe parlementaire (endpoint /organes) : groupes politiques, commissions,
    assemblées, missions, délégations…

    Le `codeType` distingue la nature de l'organe (ex. GP = groupe politique,
    COMPER = commission permanente). Les groupes votants et les mandats pointent
    vers cet identifiant `uid` (PO…) via leur `organeRefUid`.
    """

    __tablename__ = "organes"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    codeType: Mapped[str | None]
    type: Mapped[str | None]
    legislature: Mapped[int | None]
    chambre: Mapped[str | None]
    actif: Mapped[bool | None]
    regime: Mapped[str | None]
    regimeJuridique: Mapped[str | None]
    xsiType: Mapped[str | None]

    # --- Libellés ---
    libelle: Mapped[str | None] = mapped_column(Text)
    libelleEdition: Mapped[str | None] = mapped_column(Text)
    libelleAbrege: Mapped[str | None]
    libelleAbrev: Mapped[str | None]
    libelleTronque: Mapped[str | None]

    # --- Caractérisation politique (groupes) ---
    positionPolitique: Mapped[str | None]
    couleurAssociee: Mapped[str | None]
    poids: Mapped[int | None]
    preseance: Mapped[int | None]
    cohesion: Mapped[int | None]

    # --- Rattachement / contacts ---
    organeParentRefUid: Mapped[str | None] = mapped_column(index=True)
    secretaire01: Mapped[str | None]
    secretaire02: Mapped[str | None]
    siteInternet: Mapped[str | None] = mapped_column(Text)
    urlImage: Mapped[str | None]
    senatCode: Mapped[str | None]
    numCirco: Mapped[str | None]
    numDepartement: Mapped[str | None]

    # --- Compteurs d'activité ---
    nombreMembres: Mapped[int | None]
    nombreReunionsAnnuelles: Mapped[int | None]
    auditionsRealisees: Mapped[int | None]
    dossiersLoiTraites: Mapped[int | None]
    missionsDemarrees: Mapped[int | None]
    nombreAmendementsProposes: Mapped[int | None]
    nombreInterventions: Mapped[int | None]
    nombreQuestions: Mapped[int | None]
    nombreTextesLoisDeposes: Mapped[int | None]
    rapportsPublies: Mapped[int | None]

    # --- Dates ---
    dateDebut: Mapped[str | None]
    dateFin: Mapped[str | None]
    dateAgrement: Mapped[str | None]
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
