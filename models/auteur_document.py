from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class AuteurDocument(Base):
    """Auteur d'un document parlementaire (endpoint /auteursDocument).

    Relie un acteur (ou un organe) à un document (texte de loi, rapport…) avec sa
    `qualite` (auteur, rapporteur…). Sert à savoir qui dépose / porte un texte
    (`acteurRefUid` → acteurs, `documentRefUid` → documents).
    """

    __tablename__ = "auteursDocument"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    qualite: Mapped[str | None]

    # --- Rattachement (références molles indexées) ---
    acteurRefUid: Mapped[str | None] = mapped_column(index=True)
    organeRefUid: Mapped[str | None] = mapped_column(index=True)
    documentRefUid: Mapped[str | None] = mapped_column(index=True)

    # --- Dates ---
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
