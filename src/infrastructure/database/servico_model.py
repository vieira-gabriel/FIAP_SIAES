from decimal import Decimal
from uuid import UUID

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class ServicoModel(Base):
    __tablename__ = "servicos"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # O índice único vale também para o serviço excluído (RF-11).
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(Text)
    descricao: Mapped[str] = mapped_column(Text)
    # NUMERIC com 2 casas, como o objeto de valor `Valor`: sem erro de ponto flutuante (RNF-11).
    valor_base: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tempo_estimado_minutos: Mapped[int]
    ativo: Mapped[bool]
