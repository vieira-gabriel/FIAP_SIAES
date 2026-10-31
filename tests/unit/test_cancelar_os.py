from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from application.events.event_dispatcher import EventDispatcher, EventHandler
from application.handlers.alocacao_pecas_pendentes_handler import AlocacaoPecasPendentesHandler
from application.handlers.estorno_reservas_handler import EstornoReservasHandler
from application.use_cases.cancelar_os import CancelarOS
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.exceptions import (
    EntidadeNaoEncontrada,
    MotivoInvalido,
    MotivoObrigatorio,
    TransicaoDeStatusInvalida,
)
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

GERENTE_ID = uuid4()
ABERTURA = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
MOTIVO = "Cliente desistiu do serviço"


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


async def _os(ordens, itens, status=StatusOS.AGUARDANDO_APROVACAO, dias_depois=0) -> OrdemServico:
    os = OrdemServico(
        numero=NumeroOS.gerar(CPF("529.982.247-25"), uuid4()),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=status,
        data_abertura=ABERTURA + timedelta(days=dias_depois),
        pecas=itens,
    )
    await ordens.salvar(os)
    return os


@pytest.fixture
def cancelar(ordens, estoques) -> CancelarOS:
    despachador = EventDispatcher()
    despachador.registrar(OSCanceladaEvent, EstornoReservasHandler(estoques))
    despachador.registrar(SaldoPecaAtualizadoEvent, AlocacaoPecasPendentesHandler(ordens, estoques))
    return CancelarOS(ordens, despachador)


async def test_cancela_a_os_e_devolve_as_reservas_ao_saldo(cancelar, ordens, estoques):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=10, quantidade_reservada=3)
    await estoques.salvar(estoque)
    os = await _os(ordens, [_item(peca_id, 3, reservada=3)])

    cancelada = await cancelar.executar(os.id, GERENTE_ID, MOTIVO)

    assert cancelada.status is StatusOS.CANCELADA
    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (0, 10)
    registro = cancelada.historico[-1]
    assert (registro.status_novo, registro.motivo, registro.usuario_id) == (
        StatusOS.CANCELADA,
        MOTIVO,
        GERENTE_ID,
    )


async def test_cancelamento_remove_as_pendencias_da_os(cancelar, ordens, estoques):
    peca_id = uuid4()
    await estoques.salvar(EstoquePeca(peca_id=peca_id, quantidade_fisica=1, quantidade_reservada=1))
    os = await _os(ordens, [_item(peca_id, 4, reservada=1)], status=StatusOS.AGUARDANDO_PECA)

    await cancelar.executar(os.id, GERENTE_ID, MOTIVO)

    assert await ordens.listar_pendentes_da_peca(peca_id) == []


async def test_saldo_devolvido_vai_para_a_os_que_esperava_a_peca(cancelar, ordens, estoques):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=3, quantidade_reservada=3)
    await estoques.salvar(estoque)
    dona = await _os(ordens, [_item(peca_id, 3, reservada=3)])
    esperando = await _os(
        ordens, [_item(peca_id, 2, reservada=0)], status=StatusOS.AGUARDANDO_PECA, dias_depois=1
    )

    await cancelar.executar(dona.id, GERENTE_ID, MOTIVO)

    assert esperando.status is StatusOS.AGUARDANDO_EXECUCAO
    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (2, 1)


async def test_os_em_execucao_nao_devolve_as_pecas_ja_baixadas(cancelar, ordens, estoques):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=5)
    await estoques.salvar(estoque)
    os = await _os(ordens, [_item(peca_id, 3, reservada=3)], status=StatusOS.EM_EXECUCAO)

    await cancelar.executar(os.id, GERENTE_ID, MOTIVO)

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (5, 0)


async def test_os_inexistente(cancelar):
    with pytest.raises(EntidadeNaoEncontrada):
        await cancelar.executar(uuid4(), GERENTE_ID, MOTIVO)


@pytest.mark.parametrize("motivo", ["", "   "])
async def test_motivo_em_branco_e_recusado_e_nada_e_estornado(cancelar, ordens, estoques, motivo):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=3, quantidade_reservada=3)
    await estoques.salvar(estoque)
    os = await _os(ordens, [_item(peca_id, 3, reservada=3)])

    with pytest.raises(MotivoObrigatorio):
        await cancelar.executar(os.id, GERENTE_ID, motivo)

    assert (os.status, estoque.quantidade_reservada) == (StatusOS.AGUARDANDO_APROVACAO, 3)


@pytest.mark.parametrize("motivo", ["<script>alert(1)</script>", "a < b", "<"])
async def test_motivo_com_marcacao_e_recusado(cancelar, ordens, motivo):
    os = await _os(ordens, [])

    with pytest.raises(MotivoInvalido):
        await cancelar.executar(os.id, GERENTE_ID, motivo)

    assert os.status is StatusOS.AGUARDANDO_APROVACAO


@pytest.mark.parametrize("status", [StatusOS.FINALIZADA, StatusOS.ENTREGUE, StatusOS.CANCELADA])
async def test_os_em_estado_final_nao_pode_ser_cancelada(cancelar, ordens, status):
    os = await _os(ordens, [], status=status)

    with pytest.raises(TransicaoDeStatusInvalida):
        await cancelar.executar(os.id, GERENTE_ID, MOTIVO)


async def test_falha_do_estorno_sobe_para_a_unidade_de_trabalho(ordens):
    class HandlerQueFalha(EventHandler):
        async def tratar(self, evento):
            raise RuntimeError("falha no estorno")

    despachador = EventDispatcher()
    despachador.registrar(OSCanceladaEvent, HandlerQueFalha())
    os = await _os(ordens, [])

    with pytest.raises(RuntimeError):
        await CancelarOS(ordens, despachador).executar(os.id, GERENTE_ID, MOTIVO)
