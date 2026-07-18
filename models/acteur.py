from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Acteur(Base):
    """Acteur parlementaire (député / sénateur) tel que renvoyé par l'API des
    tricoteuses (endpoint /acteurs).

    Référentiel trans-législature : `uid` (PA…) est stable d'une législature à
    l'autre, le rattachement à un groupe/commission passe par la table `mandats`.
    Noms de colonnes en camelCase = clés JSON (voir Amendement pour la convention).
    """

    __tablename__ = "acteurs"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    prenom: Mapped[str | None]
    nom: Mapped[str | None]
    civ: Mapped[str | None]
    slug: Mapped[str | None]
    chambre: Mapped[str | None]
    actif: Mapped[bool | None]

    # --- État civil ---
    dateNais: Mapped[str | None]
    dateDeces: Mapped[str | None]
    villeNais: Mapped[str | None]
    depNais: Mapped[str | None]
    paysNais: Mapped[str | None]

    # --- Profession ---
    profession: Mapped[str | None]
    catSocPro: Mapped[str | None]
    famSocPro: Mapped[str | None]

    # --- Rattachements (références molles indexées) ---
    groupeParlementaireUid: Mapped[str | None] = mapped_column(index=True)
    mandatPrincipalUid: Mapped[str | None] = mapped_column(index=True)
    circonscriptionUid: Mapped[str | None] = mapped_column(index=True)
    commissionPermanenteRefUid: Mapped[str | None] = mapped_column(index=True)
    fonctionCommissionPermanente: Mapped[str | None]
    placeHemicycle: Mapped[str | None]

    # --- Divers ---
    uriHatvp: Mapped[str | None]
    urlImage: Mapped[str | None]
    compteTwitter: Mapped[str | None]
    senatMatricule: Mapped[str | None]

    # --- Compteurs d'activité ---
    nombreAmendements: Mapped[int | None]
    nombreAmendementsAdoptes: Mapped[int | None]
    nombreInterventions: Mapped[int | None]
    nombreQuestions: Mapped[int | None]
    nombreQuestionsRepondues: Mapped[int | None]
    nombreDocumentsPublies: Mapped[int | None]
    nombreMandats: Mapped[int | None]

    # --- Dates ---
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
