from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from application.use_cases.consultar_os_publica import AcompanhamentoDaOS


class ConsultaPublicaRequest(BaseModel):
    numero: str = Field(min_length=1, max_length=20, examples=["529-7F3A9C2B"])
    documento: str = Field(min_length=1, max_length=20, examples=["529.982.247-25"])


class PecaPendenteResponse(BaseModel):
    nome: str
    quantidade: int


class AcompanhamentoResponse(BaseModel):
    """O que o cliente vê da OS: sem dados pessoais, sem preços unitários e sem histórico."""

    numero: str = Field(examples=["529-7F3A9C2B"])
    status: str = Field(examples=["AGUARDANDO_PECA"])
    servicos: list[str] = Field(examples=[["Troca de óleo"]])
    pecas_pendentes: list[PecaPendenteResponse]
    valor_total: Decimal | None
    estimativa_entrega: datetime | None

    @classmethod
    def de_acompanhamento(cls, acompanhamento: AcompanhamentoDaOS) -> "AcompanhamentoResponse":
        os = acompanhamento.os
        return cls(
            numero=os.numero.valor,
            status=os.status.value,
            servicos=[item.nome for item in os.servicos],
            pecas_pendentes=[
                PecaPendenteResponse(nome=item.nome, quantidade=item.quantidade_pendente)
                for item in os.pecas
                if item.quantidade_pendente > 0
            ],
            valor_total=None if os.orcamento is None else os.orcamento.total.valor,
            estimativa_entrega=acompanhamento.estimativa_entrega,
        )
