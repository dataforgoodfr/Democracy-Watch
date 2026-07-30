from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CoSignataireDocument(Base):
    """Co-signataire d'un document parlementaire (endpoint /coSignatairesDocument).

    Relie un acteur à un document qu'il co-signe, avec les dates de (co)signature et
    d'éventuel retrait. Complète `auteursDocument` pour reconstituer l'ensemble des
    soutiens d'un texte.
    """

    __tablename__ = "coSignatairesDocument"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    edite: Mapped[bool | None]
    etApparentes: Mapped[bool | None]

    # --- Rattachement (références molles indexées) ---
    acteurRefUid: Mapped[str | None] = mapped_column(index=True)
    organeRefUid: Mapped[str | None] = mapped_column(index=True)
    documentRefUid: Mapped[str | None] = mapped_column(index=True)

    # --- Dates ---
    dateCosignature: Mapped[str | None]
    dateRetraitCosignature: Mapped[str | None]
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
