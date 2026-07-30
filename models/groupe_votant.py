from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class GroupeVotant(Base):
    """Résultat d'un scrutin ventilé par groupe politique (endpoint /groupesVotants).

    Une ligne par couple (scrutin, groupe) : le décompte du groupe et sa position
    majoritaire. Le détail nominatif (endpoint /votes) n'est pas chargé.

    L'endpoint n'expose pas de filtre `legislature` : la table couvre toutes les
    législatures et se scope à la 17ᵉ par jointure sur `scrutins`.
    """

    __tablename__ = "groupesVotants"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]

    # --- Rattachement (références molles indexées) ---
    scrutinRefUid: Mapped[str | None] = mapped_column(index=True)
    organeRefUid: Mapped[str | None] = mapped_column(index=True)

    # --- Décompte du groupe ---
    positionMajoritaire: Mapped[str | None]
    nombreMembresGroupe: Mapped[int | None]
    pour: Mapped[int | None]
    contre: Mapped[int | None]
    abstentions: Mapped[int | None]
    nonVotants: Mapped[int | None]
    nonVotantsVolontaires: Mapped[int | None]

    # --- Dates ---
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
