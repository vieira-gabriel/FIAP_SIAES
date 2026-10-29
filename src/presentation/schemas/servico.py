from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from domain.entities.servico import Servico


class ServicoRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=50, examples=["SRV-001"])
    nome: str = Field(min_length=1, max_length=200, examples=["Troca de óleo"])
    descricao: str = Field(min_length=1, max_length=2000, examples=["Troca do óleo e do filtro"])
    valor_base: Decimal = Field(examples=["120.00"])
    tempo_estimado_minutos: int = Field(examples=[45])


class ServicoResponse(BaseModel):
    id: UUID
    codigo: str
    nome: str
    descricao: str
    valor_base: Decimal = Field(examples=["120.00"])
    tempo_estimado_minutos: int

    @classmethod
    def de_entidade(cls, servico: Servico) -> "ServicoResponse":
        return cls(
            id=servico.id,
            codigo=servico.codigo,
            nome=servico.nome,
            descricao=servico.descricao,
            valor_base=servico.valor_base.valor,
            tempo_estimado_minutos=servico.tempo_estimado_minutos,
        )
