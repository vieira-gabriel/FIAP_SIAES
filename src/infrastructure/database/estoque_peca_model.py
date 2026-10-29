from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class EstoquePecaModel(Base):
    __tablename__ = "estoque_pecas"
    # Repetem as regras de `EstoquePeca` para o banco recusar saldo negativo mesmo com uma
    # escrita feita fora do domínio (RF-12).
    __table_args__ = (
        CheckConstraint("quantidade_fisica >= 0", name="ck_estoque_pecas_fisica_nao_negativa"),
        CheckConstraint(
            "quantidade_reservada >= 0", name="ck_estoque_pecas_reservada_nao_negativa"
        ),
        CheckConstraint(
            "quantidade_reservada <= quantidade_fisica",
            name="ck_estoque_pecas_reservada_ate_a_fisica",
        ),
    )

    peca_id: Mapped[UUID] = mapped_column(ForeignKey("pecas.id"), primary_key=True)
    quantidade_fisica: Mapped[int]
    quantidade_reservada: Mapped[int]
