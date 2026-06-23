"""create dossier table

Revision ID: 0b9e004cecd3
Revises:
Create Date: 2026-06-23 20:57:02.604680

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0b9e004cecd3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dossiers",
        sa.Column("uid", sa.String(50), primary_key=True),
        sa.Column("titre", sa.String(500)),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("dossiers")
