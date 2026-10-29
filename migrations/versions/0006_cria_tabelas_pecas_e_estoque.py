"""cria tabelas pecas e estoque_pecas

Cadastro de peças, com código de referência único e exclusão lógica, e o estoque de cada peça
na relação 1:1, com as quantidades física e reservada (RF-12).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pecas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo_referencia", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("preco_unitario", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("prazo_reposicao_dias", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_referencia"),
    )
    op.create_table(
        "estoque_pecas",
        sa.Column("peca_id", sa.Uuid(), nullable=False),
        sa.Column("quantidade_fisica", sa.Integer(), nullable=False),
        sa.Column("quantidade_reservada", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantidade_fisica >= 0", name="ck_estoque_pecas_fisica_nao_negativa"),
        sa.CheckConstraint(
            "quantidade_reservada >= 0", name="ck_estoque_pecas_reservada_nao_negativa"
        ),
        sa.CheckConstraint(
            "quantidade_reservada <= quantidade_fisica",
            name="ck_estoque_pecas_reservada_ate_a_fisica",
        ),
        sa.ForeignKeyConstraint(["peca_id"], ["pecas.id"]),
        sa.PrimaryKeyConstraint("peca_id"),
    )


def downgrade() -> None:
    op.drop_table("estoque_pecas")
    op.drop_table("pecas")
