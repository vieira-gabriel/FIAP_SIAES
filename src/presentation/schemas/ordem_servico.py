from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from application.use_cases.detalhar_ordem_servico import DetalheDaOrdemServico
from application.use_cases.listar_ordens_servico import ResumoDaOrdemServico
from domain.entities.ordem_servico import OrdemServico

_MAIOR_INTEIRO = 2_147_483_647


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


class AtribuirMecanicoRequest(BaseModel):
    """O Mecânico omite o campo, porque atribui a OS a si mesmo; o Gerente informa o mecânico."""

    mecanico_id: UUID | None = None


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


class OSResumoResponse(BaseModel):
    id: UUID
    numero: str = Field(examples=["529-7F3A9C2B"])
    status: str = Field(examples=["RECEBIDA"])
    cliente_nome: str
    placa: str
    mecanico_nome: str | None
    data_abertura: datetime
    valor_total: Decimal | None

    @classmethod
    def de_resumo(cls, resumo: ResumoDaOrdemServico) -> "OSResumoResponse":
        os = resumo.os
        return cls(
            id=os.id,
            numero=os.numero.valor,
            status=os.status.value,
            cliente_nome=resumo.cliente.nome,
            placa=resumo.veiculo.placa.valor,
            mecanico_nome=resumo.mecanico.nome if resumo.mecanico else None,
            data_abertura=os.data_abertura,
            valor_total=os.orcamento.total.valor if os.orcamento else None,
        )


class ClienteResumo(BaseModel):
    id: UUID
    nome: str


class VeiculoResumo(BaseModel):
    id: UUID
    placa: str
    marca: str
    modelo: str


class ItemServicoResponse(BaseModel):
    servico_id: UUID
    nome: str
    preco_congelado: Decimal
    tempo_estimado_minutos: int


class ItemPecaResponse(BaseModel):
    peca_id: UUID
    nome: str
    quantidade: int
    preco_unitario_congelado: Decimal
    prazo_reposicao_dias: int
    quantidade_reservada: int
    quantidade_pendente: int


class OrcamentoResponse(BaseModel):
    subtotal_servicos: Decimal
    subtotal_pecas: Decimal
    total: Decimal


class RegistroHistoricoResponse(BaseModel):
    status_anterior: str | None
    status_novo: str
    data_hora: datetime
    origem: str
    usuario_id: UUID | None
    motivo: str | None


class OSDetalheResponse(BaseModel):
    id: UUID
    numero: str
    status: str
    data_abertura: datetime
    data_inicio_execucao: datetime | None
    data_finalizacao: datetime | None
    cliente: ClienteResumo
    veiculo: VeiculoResumo
    atendente_id: UUID
    mecanico_id: UUID | None
    servicos: list[ItemServicoResponse]
    pecas: list[ItemPecaResponse]
    orcamento: OrcamentoResponse | None
    estimativa_entrega: datetime | None
    historico: list[RegistroHistoricoResponse]

    @classmethod
    def de_detalhe(cls, detalhe: DetalheDaOrdemServico) -> "OSDetalheResponse":
        os = detalhe.os
        return cls(
            id=os.id,
            numero=os.numero.valor,
            status=os.status.value,
            data_abertura=os.data_abertura,
            data_inicio_execucao=os.data_inicio_execucao,
            data_finalizacao=os.data_finalizacao,
            cliente=ClienteResumo(id=detalhe.cliente.id, nome=detalhe.cliente.nome),
            veiculo=VeiculoResumo(
                id=detalhe.veiculo.id,
                placa=detalhe.veiculo.placa.valor,
                marca=detalhe.veiculo.marca,
                modelo=detalhe.veiculo.modelo,
            ),
            atendente_id=os.atendente_id,
            mecanico_id=os.mecanico_id,
            servicos=_servicos_da_os(os),
            pecas=_pecas_da_os(os),
            orcamento=_orcamento_da_os(os),
            estimativa_entrega=detalhe.estimativa_entrega,
            historico=[
                RegistroHistoricoResponse(
                    status_anterior=r.status_anterior.value if r.status_anterior else None,
                    status_novo=r.status_novo.value,
                    data_hora=r.data_hora,
                    origem=r.origem.value,
                    usuario_id=r.usuario_id,
                    motivo=r.motivo,
                )
                for r in os.historico
            ],
        )


class IncluirServicoRequest(BaseModel):
    servico_id: UUID


class IncluirPecaRequest(BaseModel):
    peca_id: UUID
    quantidade: int = Field(le=_MAIOR_INTEIRO, examples=[2])


class OSItensResponse(BaseModel):
    """A OS depois de uma mudança nos itens ou na conclusão do orçamento: o status, os itens e o
    orçamento (nulo enquanto os valores não foram congelados)."""

    id: UUID
    numero: str = Field(examples=["529-7F3A9C2B"])
    status: str = Field(examples=["EM_DIAGNOSTICO"])
    servicos: list[ItemServicoResponse]
    pecas: list[ItemPecaResponse]
    orcamento: OrcamentoResponse | None

    @classmethod
    def de_entidade(cls, os: OrdemServico) -> "OSItensResponse":
        return cls(
            id=os.id,
            numero=os.numero.valor,
            status=os.status.value,
            servicos=_servicos_da_os(os),
            pecas=_pecas_da_os(os),
            orcamento=_orcamento_da_os(os),
        )


def _servicos_da_os(os: OrdemServico) -> list[ItemServicoResponse]:
    return [
        ItemServicoResponse(
            servico_id=item.servico_id,
            nome=item.nome,
            preco_congelado=item.preco_congelado.valor,
            tempo_estimado_minutos=item.tempo_estimado_minutos,
        )
        for item in os.servicos
    ]


def _pecas_da_os(os: OrdemServico) -> list[ItemPecaResponse]:
    return [
        ItemPecaResponse(
            peca_id=item.peca_id,
            nome=item.nome,
            quantidade=item.quantidade,
            preco_unitario_congelado=item.preco_unitario_congelado.valor,
            prazo_reposicao_dias=item.prazo_reposicao_dias,
            quantidade_reservada=item.quantidade_reservada,
            quantidade_pendente=item.quantidade_pendente,
        )
        for item in os.pecas
    ]


def _orcamento_da_os(os: OrdemServico) -> OrcamentoResponse | None:
    if os.orcamento is None:
        return None
    return OrcamentoResponse(
        subtotal_servicos=os.orcamento.subtotal_servicos.valor,
        subtotal_pecas=os.orcamento.subtotal_pecas.valor,
        total=os.orcamento.total.valor,
    )
