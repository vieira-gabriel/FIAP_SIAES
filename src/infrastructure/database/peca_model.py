from decimal import Decimal
from uuid import UUID

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class PecaModel(Base):
    __tablename__ = "pecas"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # O índice único vale também para a peça excluída (RF-12).
    codigo_referencia: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(Text)
    # NUMERIC com 2 casas, como o objeto de valor `Valor`: sem erro de ponto flutuante (RNF-11).
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    prazo_reposicao_dias: Mapped[int]
    ativo: Mapped[bool]
