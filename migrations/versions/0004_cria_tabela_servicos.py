"""cria tabela servicos

Catálogo de serviços da oficina, com código único e exclusão lógica (RF-10, RF-11).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 18:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "servicos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("valor_base", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tempo_estimado_minutos", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )


def downgrade() -> None:
    op.drop_table("servicos")
