from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS
from infrastructure.database.base import Base


def _status(nome: str) -> Enum:
    # VARCHAR com CHECK em vez de tipo ENUM do PostgreSQL: incluir um status não exige ALTER TYPE.
    # O nome vira o da restrição, que precisa ser único na tabela.
    return Enum(StatusOS, name=nome, native_enum=False, create_constraint=True, length=20)


class OrdemServicoModel(Base):
    """Tabela da raiz do agregado; os itens e o histórico só são gravados junto com ela."""

    __tablename__ = "ordens_servico"
    __table_args__ = (
        CheckConstraint(
            "(subtotal_servicos IS NULL) = (subtotal_pecas IS NULL)",
            name="ck_ordens_servico_orcamento_completo",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(12), unique=True)
    cliente_id: Mapped[UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    veiculo_id: Mapped[UUID] = mapped_column(ForeignKey("veiculos.id"), index=True)
    atendente_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"))
    mecanico_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    status: Mapped[StatusOS] = mapped_column(_status("status_os"))
    data_abertura: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_inicio_execucao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_finalizacao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Os subtotais do `Orcamento`; os dois nulos indicam que o orçamento não foi calculado ou foi
    # descartado por uma mudança nos itens (RF-17, RNF-11).
    subtotal_servicos: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    subtotal_pecas: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    servicos: Mapped[list["ItemServicoModel"]] = relationship(cascade="all, delete-orphan")
    pecas: Mapped[list["ItemPecaModel"]] = relationship(cascade="all, delete-orphan")
    # Só leitura: o adaptador insere os registros novos à parte, e o `merge` da OS nunca chega a
    # atualizar nem a desvincular um registro já gravado (RF-24).
    historico: Mapped[list["HistoricoStatusOSModel"]] = relationship(viewonly=True)


class ItemServicoModel(Base):
    __tablename__ = "itens_servico"

    os_id: Mapped[UUID] = mapped_column(ForeignKey("ordens_servico.id"), primary_key=True)
    servico_id: Mapped[UUID] = mapped_column(ForeignKey("servicos.id"), primary_key=True)
    nome: Mapped[str] = mapped_column(Text)
    preco_congelado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tempo_estimado_minutos: Mapped[int]


class ItemPecaModel(Base):
    __tablename__ = "itens_peca"
    # Repetem as regras de `ItemPeca` para o banco recusar quantidades inconsistentes mesmo com
    # uma escrita feita fora do domínio (RF-18).
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_itens_peca_quantidade_positiva"),
        CheckConstraint("quantidade_reservada >= 0", name="ck_itens_peca_reservada_nao_negativa"),
        CheckConstraint("quantidade_pendente >= 0", name="ck_itens_peca_pendente_nao_negativa"),
        CheckConstraint(
            "quantidade_reservada + quantidade_pendente <= quantidade",
            name="ck_itens_peca_reservada_e_pendente_ate_a_quantidade",
        ),
    )

    os_id: Mapped[UUID] = mapped_column(ForeignKey("ordens_servico.id"), primary_key=True)
    peca_id: Mapped[UUID] = mapped_column(ForeignKey("pecas.id"), primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(Text)
    quantidade: Mapped[int]
    preco_unitario_congelado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    prazo_reposicao_dias: Mapped[int]
    quantidade_reservada: Mapped[int]
    quantidade_pendente: Mapped[int]


class HistoricoStatusOSModel(Base):
    """Só aceita inserção: os triggers da migration recusam UPDATE, DELETE e TRUNCATE (RF-24)."""

    __tablename__ = "historico_status_os"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    os_id: Mapped[UUID] = mapped_column(ForeignKey("ordens_servico.id"), index=True)
    status_anterior: Mapped[StatusOS | None] = mapped_column(_status("status_anterior_os"))
    status_novo: Mapped[StatusOS] = mapped_column(_status("status_novo_os"))
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    origem: Mapped[OrigemTransicao] = mapped_column(
        Enum(
            OrigemTransicao,
            name="origem_transicao",
            native_enum=False,
            create_constraint=True,
            length=20,
        )
    )
    usuario_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    motivo: Mapped[str | None] = mapped_column(Text)
