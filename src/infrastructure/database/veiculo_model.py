from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class VeiculoModel(Base):
    __tablename__ = "veiculos"
    # Índice parcial: a placa de um veículo excluído pode ser recadastrada, por exemplo para o
    # novo dono de um carro vendido, e as OS antigas continuam no registro excluído (RF-07, RF-09).
    __table_args__ = (
        Index(
            "uq_veiculos_placa_ativa",
            "placa",
            unique=True,
            postgresql_where=text("ativo"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    placa: Mapped[str] = mapped_column(String(7))
    marca: Mapped[str] = mapped_column(String(100))
    modelo: Mapped[str] = mapped_column(String(100))
    ano: Mapped[int]
    ativo: Mapped[bool]
