from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Amendement(Base):
    """Amendement brut tel que renvoyé par l'API des tricoteuses (endpoint /amendements).

    Les noms d'attributs sont en camelCase afin de correspondre exactement aux clés
    du JSON source : l'ETL (etl/extraction.py) s'appuie sur cette correspondance
    1:1 entre nom de colonne et nom de champ JSON.

    Seul `uid` est non nullable (clé primaire) ; les autres champs restent nullable
    car les amendements sont hétérogènes (budgétaires, sous-amendements...) et
    n'exposent pas toujours l'ensemble des champs.
    """

    __tablename__ = "amendements"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    numeroLong: Mapped[str | None]
    numeroOrdreDepot: Mapped[int | None]
    legislature: Mapped[int | None]
    chambre: Mapped[str | None]
    dataset: Mapped[int | None]

    # --- Texte (contenu analysé) ---
    exposeSommaire: Mapped[str | None] = mapped_column(Text)
    dispositif: Mapped[str | None] = mapped_column(Text)

    # --- Auteur / signataires ---
    acteurRefUid: Mapped[str | None]
    groupePolitiqueRefUid: Mapped[str | None]
    organeRefUid: Mapped[str | None]
    typeAuteur: Mapped[str | None]
    nomRepresentation: Mapped[str | None]
    signatairesLibelle: Mapped[str | None]
    nombreCoSignataires: Mapped[int | None]

    # --- Objet visé dans le texte ---
    divisionArticleDesignation: Mapped[str | None]
    alineaDesignation: Mapped[str | None]

    # --- Rattachement (références molles vers d'autres entités de l'API) ---
    dossierRefUid: Mapped[str | None]
    documentRefUid: Mapped[str | None]
    etapeLegislativeRefUid: Mapped[str | None]
    codeEtape: Mapped[str | None]
    seanceRefUid: Mapped[str | None]
    # Renseigné quand l'amendement a été tranché par un scrutin public. Couvre deux
    # fois plus d'amendements que le lien inverse `scrutins.amendementRefUid`, un même
    # scrutin pouvant trancher plusieurs amendements identiques.
    scrutinRefUid: Mapped[str | None] = mapped_column(index=True)

    # --- Statut / sort ---
    sortAmendement: Mapped[str | None]
    etatCode: Mapped[str | None]
    etatLibelle: Mapped[str | None]
    triAmendement: Mapped[str | None]
    # L'API renvoie ici les chaînes "true"/"false" et non un booléen JSON.
    soumisArticle40: Mapped[str | None]

    # --- Dates (conservées en texte : l'ETL insère les valeurs JSON brutes) ---
    dateDepot: Mapped[str | None]
    dateSort: Mapped[str | None]
    dateMaj: Mapped[str | None]
    datePublication: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
