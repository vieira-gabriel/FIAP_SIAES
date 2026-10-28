"""cria tabela veiculos

Veículos vinculados ao cliente, com placa única entre os ativos e exclusão lógica (RF-07 a RF-09).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 15:00:00

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
        "veiculos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("placa", sa.String(length=7), nullable=False),
        sa.Column("marca", sa.String(length=100), nullable=False),
        sa.Column("modelo", sa.String(length=100), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_veiculos_cliente_id"), "veiculos", ["cliente_id"], unique=False)
    op.create_index(
        "uq_veiculos_placa_ativa",
        "veiculos",
        ["placa"],
        unique=True,
        postgresql_where=sa.text("ativo"),
    )


def downgrade() -> None:
    op.drop_index("uq_veiculos_placa_ativa", table_name="veiculos")
    op.drop_index(op.f("ix_veiculos_cliente_id"), table_name="veiculos")
    op.drop_table("veiculos")
