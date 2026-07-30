from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class AmendementMention(Base):
    """Mention de collaboration externe détectée dans l'exposé sommaire d'un amendement.

    Table d'ANALYSE (pas alimentée par l'ETL) : elle n'est donc pas listée dans
    ETL_TABLES et survit aux rebuilds. Un amendement peut porter plusieurs mentions,
    d'où une clé primaire de substitution et une ligne par mention.

    `amendementUid` est une référence molle vers `amendements.uid` (pas de ForeignKey) :
    la table `amendements` étant recréée à chaque rebuild, une contrainte référentielle
    bloquerait son drop. On suit ici la même logique que les RefUid du modèle Amendement.

    Les champs métier reprennent le schéma produit par le détecteur
    (analysis/detect_mentions_regex.py).
    """

    __tablename__ = "amendement_mentions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Référence molle vers amendements.uid (indexée pour les jointures applicatives).
    amendementUid: Mapped[str] = mapped_column(index=True)

    # Passage exact recopié depuis l'exposé sommaire.
    citation: Mapped[str] = mapped_column(Text)
    # Expression déclencheuse, ex. « travaillé avec », « en lien avec ».
    formulation: Mapped[str | None]
    # Nom de l'entité citée, ou NULL si non nommée.
    entite: Mapped[str | None]
    # lobby|association|syndicat|entreprise|federation_professionnelle|ong|
    # think_tank|collectif_citoyen|organe_public|autre|inconnu
    typeEntite: Mapped[str | None]
    # True si acteur d'intérêt privé/externe, False si institution publique.
    externe: Mapped[bool | None] = mapped_column(Boolean)

    # Provenance : le modèle varie pendant le POC, on trace ce qui a produit la ligne.
    modele: Mapped[str | None]
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
