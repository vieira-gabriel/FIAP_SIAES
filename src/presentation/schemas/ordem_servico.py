from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from domain.entities.ordem_servico import OrdemServico


class ClienteNovoRequest(BaseModel):
    """Dados para cadastrar o cliente no mesmo fluxo, quando o documento ainda não existe."""

    nome: str = Field(min_length=1, max_length=200, examples=["Maria Silva"])
    email: str = Field(min_length=3, max_length=254, examples=["maria@exemplo.com"])
    telefone: str = Field(min_length=1, max_length=30, examples=["(11) 98765-4321"])


class VeiculoNovoRequest(BaseModel):
    """Dados para cadastrar o veículo no mesmo fluxo, quando a placa ainda não existe."""

    marca: str = Field(min_length=1, max_length=50, examples=["Fiat"])
    modelo: str = Field(min_length=1, max_length=100, examples=["Uno"])
    ano: int = Field(examples=[2015])


class AbrirOSRequest(BaseModel):
    documento: str = Field(min_length=1, max_length=20, examples=["529.982.247-25"])
    placa: str = Field(min_length=1, max_length=12, examples=["ABC1D23"])
    cliente: ClienteNovoRequest | None = None
    veiculo: VeiculoNovoRequest | None = None


class OSResponse(BaseModel):
    id: UUID
    numero: str = Field(examples=["529-7F3A9C2B"])
    status: str = Field(examples=["RECEBIDA"])
    cliente_id: UUID
    veiculo_id: UUID
    atendente_id: UUID
    mecanico_id: UUID | None
    data_abertura: datetime

    @classmethod
    def de_entidade(cls, os: OrdemServico) -> "OSResponse":
        return cls(
            id=os.id,
            numero=os.numero.valor,
            status=os.status.value,
            cliente_id=os.cliente_id,
            veiculo_id=os.veiculo_id,
            atendente_id=os.atendente_id,
            mecanico_id=os.mecanico_id,
            data_abertura=os.data_abertura,
        )
