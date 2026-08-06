from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ActeLegislatif(Base):
    """Acte de la procédure (endpoint /actesLegislatifs) : un événement daté du
    parcours d'un dossier (dépôt, renvoi en commission, réunion, séance, décision,
    saisine du Conseil constitutionnel, promulgation…).

    Les actes forment un arbre via `parentUid`, dont la racine est l'étape de
    navette (`codeActe` = AN1, SN1, CMP, ANNLEC, ANLDEF, CC, PROM…) et les feuilles
    le détail des travaux. `libelleStatutConclusion` ne porte que sur les actes de
    décision (`*-DEC`) : c'est là que se lit « adoptée », « rejetée », « Désaccord ».

    Seuls les champs utiles à la reconstitution du parcours sont chargés ; l'endpoint
    en expose une soixantaine.
    """

    __tablename__ = "actesLegislatifs"

    # --- Identité ---
    uid: Mapped[str] = mapped_column(primary_key=True)
    dataset: Mapped[int | None]
    legislature: Mapped[int | None]
    chambre: Mapped[str | None]
    codeActe: Mapped[str | None] = mapped_column(index=True)
    nomCanonique: Mapped[str | None] = mapped_column(String(1000))
    libelleCourtActe: Mapped[str | None] = mapped_column(String(1000))
    xsiType: Mapped[str | None]

    # --- Position dans l'arbre des actes ---
    parentUid: Mapped[str | None] = mapped_column(index=True)
    dossierRefUid: Mapped[str | None] = mapped_column(index=True)
    etapeLegislativeRefUid: Mapped[str | None]

    # --- Conclusion (actes de décision uniquement) ---
    libelleStatutConclusion: Mapped[str | None] = mapped_column(String(1000))
    libelleDecision: Mapped[str | None] = mapped_column(String(1000))

    # --- Rattachements ---
    organeRefUid: Mapped[str | None]
    documentRefUid: Mapped[str | None]
    texteAdopteRefUid: Mapped[str | None]
    texteAssocieRefUid: Mapped[str | None]

    # --- Dates ---
    dateActe: Mapped[str | None]
    dateJo: Mapped[str | None]
    dateMaj: Mapped[str | None]
    datePremierAjout: Mapped[str | None]
