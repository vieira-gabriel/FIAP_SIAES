"""cria tabela clientes

Clientes da oficina, com documento único e exclusão lógica (RF-04 a RF-06).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("documento", sa.String(length=14), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("telefone", sa.String(length=30), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("documento"),
    )


def downgrade() -> None:
    op.drop_table("clientes")
