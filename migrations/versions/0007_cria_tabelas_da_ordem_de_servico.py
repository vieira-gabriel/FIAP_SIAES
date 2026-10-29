"""cria tabelas da ordem de servico

Ordens de serviço com número único, itens de serviço e de peça com os valores congelados e o
histórico de status, que só aceita inserção (RF-13, RF-17, RF-24, RNF-11).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-29 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS_OS = (
    "RECEBIDA",
    "EM_DIAGNOSTICO",
    "AGUARDANDO_APROVACAO",
    "AGUARDANDO_PECA",
    "AGUARDANDO_EXECUCAO",
    "EM_EXECUCAO",
    "FINALIZADA",
    "ENTREGUE",
    "CANCELADA",
)


def _status(nome: str) -> sa.Enum:
    return sa.Enum(*_STATUS_OS, name=nome, native_enum=False, create_constraint=True, length=20)


def upgrade() -> None:
    op.create_table(
        "ordens_servico",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("numero", sa.String(length=12), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("veiculo_id", sa.Uuid(), nullable=False),
        sa.Column("atendente_id", sa.Uuid(), nullable=False),
        sa.Column("mecanico_id", sa.Uuid(), nullable=True),
        sa.Column("status", _status("status_os"), nullable=False),
        sa.Column("data_abertura", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_inicio_execucao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_finalizacao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subtotal_servicos", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("subtotal_pecas", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.CheckConstraint(
            "(subtotal_servicos IS NULL) = (subtotal_pecas IS NULL)",
            name="ck_ordens_servico_orcamento_completo",
        ),
        sa.ForeignKeyConstraint(["atendente_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["mecanico_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["veiculo_id"], ["veiculos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero"),
    )
    op.create_index(
        op.f("ix_ordens_servico_cliente_id"), "ordens_servico", ["cliente_id"], unique=False
    )
    op.create_index(
        op.f("ix_ordens_servico_veiculo_id"), "ordens_servico", ["veiculo_id"], unique=False
    )
    op.create_table(
        "itens_servico",
        sa.Column("os_id", sa.Uuid(), nullable=False),
        sa.Column("servico_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("preco_congelado", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tempo_estimado_minutos", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["os_id"], ["ordens_servico.id"]),
        sa.ForeignKeyConstraint(["servico_id"], ["servicos.id"]),
        sa.PrimaryKeyConstraint("os_id", "servico_id"),
    )
    op.create_table(
        "itens_peca",
        sa.Column("os_id", sa.Uuid(), nullable=False),
        sa.Column("peca_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("preco_unitario_congelado", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("prazo_reposicao_dias", sa.Integer(), nullable=False),
        sa.Column("quantidade_reservada", sa.Integer(), nullable=False),
        sa.Column("quantidade_pendente", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantidade > 0", name="ck_itens_peca_quantidade_positiva"),
        sa.CheckConstraint(
            "quantidade_reservada >= 0", name="ck_itens_peca_reservada_nao_negativa"
        ),
        sa.CheckConstraint("quantidade_pendente >= 0", name="ck_itens_peca_pendente_nao_negativa"),
        sa.CheckConstraint(
            "quantidade_reservada + quantidade_pendente <= quantidade",
            name="ck_itens_peca_reservada_e_pendente_ate_a_quantidade",
        ),
        sa.ForeignKeyConstraint(["os_id"], ["ordens_servico.id"]),
        sa.ForeignKeyConstraint(["peca_id"], ["pecas.id"]),
        sa.PrimaryKeyConstraint("os_id", "peca_id"),
    )
    op.create_index(op.f("ix_itens_peca_peca_id"), "itens_peca", ["peca_id"], unique=False)
    op.create_table(
        "historico_status_os",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("os_id", sa.Uuid(), nullable=False),
        sa.Column("status_anterior", _status("status_anterior_os"), nullable=True),
        sa.Column("status_novo", _status("status_novo_os"), nullable=False),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "origem",
            sa.Enum(
                "USUARIO",
                "CLIENTE",
                "SISTEMA",
                name="origem_transicao",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["os_id"], ["ordens_servico.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_historico_status_os_os_id"), "historico_status_os", ["os_id"], unique=False
    )
    # O autogenerate não compara triggers; o teste de integração do histórico cobre esta parte.
    op.execute(
        """
        CREATE FUNCTION historico_status_os_somente_insercao() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'o histórico de status da OS só aceita inserção (RF-24)';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER historico_status_os_somente_insercao
        BEFORE UPDATE OR DELETE ON historico_status_os
        FOR EACH ROW EXECUTE FUNCTION historico_status_os_somente_insercao()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER historico_status_os_somente_insercao ON historico_status_os")
    op.execute("DROP FUNCTION historico_status_os_somente_insercao()")
    op.drop_index(op.f("ix_historico_status_os_os_id"), table_name="historico_status_os")
    op.drop_table("historico_status_os")
    op.drop_index(op.f("ix_itens_peca_peca_id"), table_name="itens_peca")
    op.drop_table("itens_peca")
    op.drop_table("itens_servico")
    op.drop_index(op.f("ix_ordens_servico_veiculo_id"), table_name="ordens_servico")
    op.drop_index(op.f("ix_ordens_servico_cliente_id"), table_name="ordens_servico")
    op.drop_table("ordens_servico")
