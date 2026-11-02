from uuid import UUID, uuid4

import pytest

from application.events.event_dispatcher import EventDispatcher
from application.handlers.alocacao_pecas_pendentes_handler import AlocacaoPecasPendentesHandler
from application.handlers.estorno_reservas_handler import EstornoReservasHandler
from application.use_cases.aprovar_orcamento_no_balcao import AprovarOrcamentoNoBalcao
from application.use_cases.rejeitar_orcamento_no_balcao import RejeitarOrcamentoNoBalcao
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.exceptions import EntidadeNaoEncontrada, TransicaoDeStatusInvalida
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

ATENDENTE_ID = uuid4()


def _item(peca_id: UUID, quantidade: int, reservada: int) -> ItemPeca:
    return ItemPeca(
        peca_id=peca_id,
        nome="Filtro de óleo",
        quantidade=quantidade,
        preco_unitario_congelado=Valor("35.90"),
        prazo_reposicao_dias=3,
        quantidade_reservada=reservada,
        quantidade_pendente=quantidade - reservada,
    )


async def _os(ordens, itens=(), status=StatusOS.AGUARDANDO_APROVACAO) -> OrdemServico:
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=status,
        pecas=list(itens),
    )
    await ordens.salvar(os)
    return os


@pytest.fixture
def aprovar(ordens) -> AprovarOrcamentoNoBalcao:
    return AprovarOrcamentoNoBalcao(ordens)


@pytest.fixture
def rejeitar(ordens, estoques) -> RejeitarOrcamentoNoBalcao:
    despachador = EventDispatcher()
    despachador.registrar(OSCanceladaEvent, EstornoReservasHandler(estoques))
    despachador.registrar(SaldoPecaAtualizadoEvent, AlocacaoPecasPendentesHandler(ordens, estoques))
    return RejeitarOrcamentoNoBalcao(ordens, despachador)


async def test_aprovacao_no_balcao_grava_o_funcionario_no_historico(aprovar, ordens):
    os = await _os(ordens)

    aprovada = await aprovar.executar(os.id, ATENDENTE_ID)

    assert aprovada.status is StatusOS.AGUARDANDO_EXECUCAO
    registro = aprovada.historico[-1]
    assert (registro.origem, registro.usuario_id) == (OrigemTransicao.USUARIO, ATENDENTE_ID)


async def test_aprovacao_no_balcao_com_peca_pendente_aguarda_a_peca(aprovar, ordens):
    os = await _os(ordens, [_item(uuid4(), 2, reservada=0)])

    await aprovar.executar(os.id, ATENDENTE_ID)

    assert os.status is StatusOS.AGUARDANDO_PECA


async def test_rejeicao_no_balcao_cancela_e_devolve_as_reservas(rejeitar, ordens, estoques):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=5, quantidade_reservada=2)
    await estoques.salvar(estoque)
    os = await _os(ordens, [_item(peca_id, 2, reservada=2)])

    rejeitada = await rejeitar.executar(os.id, ATENDENTE_ID)

    assert rejeitada.status is StatusOS.CANCELADA
    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (0, 5)
    registro = rejeitada.historico[-1]
    assert (registro.origem, registro.usuario_id) == (OrigemTransicao.USUARIO, ATENDENTE_ID)


@pytest.mark.parametrize("decisao", ["aprovar", "rejeitar"])
async def test_decisao_so_a_partir_de_aguardando_aprovacao(decisao, request, ordens):
    caso_de_uso = request.getfixturevalue(decisao)
    os = await _os(ordens, status=StatusOS.AGUARDANDO_EXECUCAO)

    with pytest.raises(TransicaoDeStatusInvalida):
        await caso_de_uso.executar(os.id, ATENDENTE_ID)

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO


@pytest.mark.parametrize("decisao", ["aprovar", "rejeitar"])
async def test_os_inexistente(decisao, request):
    caso_de_uso = request.getfixturevalue(decisao)

    with pytest.raises(EntidadeNaoEncontrada):
        await caso_de_uso.executar(uuid4(), ATENDENTE_ID)
