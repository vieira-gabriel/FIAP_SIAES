from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from domain.entities.estoque_peca import EstoquePeca
from domain.entities.peca import Peca


class PecaRequest(BaseModel):
    codigo_referencia: str = Field(min_length=1, max_length=50, examples=["FLT-001"])
    nome: str = Field(min_length=1, max_length=200, examples=["Filtro de óleo"])
    preco_unitario: Decimal = Field(examples=["35.90"])
    prazo_reposicao_dias: int = Field(examples=[3])


class CadastrarPecaRequest(PecaRequest):
    quantidade_fisica_inicial: int = Field(default=0, examples=[10])


class ReposicaoRequest(BaseModel):
    quantidade: int = Field(examples=[5])


class AjusteQuantidadeFisicaRequest(BaseModel):
    quantidade_fisica: int = Field(examples=[8])


class PecaResponse(BaseModel):
    id: UUID
    codigo_referencia: str
    nome: str
    preco_unitario: Decimal = Field(examples=["35.90"])
    prazo_reposicao_dias: int
    quantidade_fisica: int
    quantidade_reservada: int
    saldo_disponivel: int

    @classmethod
    def de_entidades(cls, peca: Peca, estoque: EstoquePeca) -> "PecaResponse":
        return cls(
            id=peca.id,
            codigo_referencia=peca.codigo_referencia,
            nome=peca.nome,
            preco_unitario=peca.preco_unitario.valor,
            prazo_reposicao_dias=peca.prazo_reposicao_dias,
            quantidade_fisica=estoque.quantidade_fisica,
            quantidade_reservada=estoque.quantidade_reservada,
            saldo_disponivel=estoque.saldo_disponivel(),
        )
