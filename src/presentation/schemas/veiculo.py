from uuid import UUID

from pydantic import BaseModel, Field

from domain.entities.veiculo import Veiculo


class AtualizarVeiculoRequest(BaseModel):
    """A placa pode vir com minúsculas, hífen ou espaços; o domínio a normaliza (RF-08)."""

    placa: str = Field(min_length=1, max_length=10, examples=["ABC-1D23"])
    marca: str = Field(min_length=1, max_length=100, examples=["Fiat"])
    modelo: str = Field(min_length=1, max_length=100, examples=["Uno"])
    ano: int = Field(examples=[2015])


class CadastrarVeiculoRequest(AtualizarVeiculoRequest):
    cliente_id: UUID


class VeiculoResponse(BaseModel):
    id: UUID
    cliente_id: UUID
    placa: str = Field(examples=["ABC1D23"])
    marca: str
    modelo: str
    ano: int

    @classmethod
    def de_entidade(cls, veiculo: Veiculo) -> "VeiculoResponse":
        return cls(
            id=veiculo.id,
            cliente_id=veiculo.cliente_id,
            placa=veiculo.placa.valor,
            marca=veiculo.marca,
            modelo=veiculo.modelo,
            ano=veiculo.ano,
        )
