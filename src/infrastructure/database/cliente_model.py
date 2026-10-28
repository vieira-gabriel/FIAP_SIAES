from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class ClienteModel(Base):
    __tablename__ = "clientes"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(Text)
    # Só os dígitos: 11 para CPF e 14 para CNPJ. O tamanho indica o tipo, por isso não há coluna
    # de tipo. O índice único vale também para o cliente excluído (RF-06).
    documento: Mapped[str] = mapped_column(String(14), unique=True)
    email: Mapped[str] = mapped_column(String(254))
    telefone: Mapped[str] = mapped_column(String(30))
    ativo: Mapped[bool]
