from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Dossier(Base):
    """Dossier législatif (endpoint /dossiers) : le fil qui suit un texte tout au long
    de la procédure (commission, séance, navette avec le Sénat, amendements...).

    L'endpoint expose bien plus de champs que ceux repris ici ; on ne charge que ceux
    utiles aux recoupements.
    """

    __tablename__ = "dossiers"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(1000))
    dataset: Mapped[int]
    legislature: Mapped[int | None]

    # --- Procédure ---
    codeProcedure: Mapped[str | None]
    libelleProcedure: Mapped[str | None]

    # --- Avancement ---
    statut: Mapped[str | None]
    dateDernierActe: Mapped[str | None]
