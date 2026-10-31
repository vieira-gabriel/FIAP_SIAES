from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from application.handlers.alocacao_pecas_pendentes_handler import AlocacaoPecasPendentesHandler
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

ABERTURA = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)


def _item(peca_id: UUID, quantidade: int, reservada: int = 0) -> ItemPeca:
    return ItemPeca(
        peca_id=peca_id,
        nome="Filtro de óleo",
        quantidade=quantidade,
        preco_unitario_congelado=Valor("35.90"),
        prazo_reposicao_dias=3,
        quantidade_reservada=reservada,
        quantidade_pendente=quantidade - reservada,
    )


async def _os(
    ordens,
    itens: list[ItemPeca],
    status: StatusOS = StatusOS.AGUARDANDO_PECA,
    dias_depois: int = 0,
) -> OrdemServico:
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


async def _estoque(estoques, peca_id: UUID, fisica: int, reservada: int = 0) -> EstoquePeca:
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=fisica, quantidade_reservada=reservada)
    await estoques.salvar(estoque)
    return estoque


def _evento(peca_id: UUID, saldo: int = 0) -> SaldoPecaAtualizadoEvent:
    return SaldoPecaAtualizadoEvent(peca_id=peca_id, saldo_disponivel=saldo)


@pytest.fixture
def alocar(ordens, estoques) -> AlocacaoPecasPendentesHandler:
    return AlocacaoPecasPendentesHandler(ordens, estoques)


async def _situacao(ordens, os_id: UUID, peca_id: UUID) -> tuple[StatusOS, int, int]:
    os = await ordens.buscar_por_id(os_id)
    (item,) = [i for i in os.pecas if i.peca_id == peca_id]
    return os.status, item.quantidade_reservada, item.quantidade_pendente


async def test_o_saldo_da_reposicao_completa_a_os_e_a_libera_para_a_execucao(
    alocar, ordens, estoques
):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=3)
    os = await _os(ordens, [_item(peca_id, 3)])

    eventos = await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, os.id, peca_id) == (StatusOS.AGUARDANDO_EXECUCAO, 3, 0)
    registro = (await ordens.buscar_por_id(os.id)).historico[-1]
    assert (registro.status_anterior, registro.status_novo) == (
        StatusOS.AGUARDANDO_PECA,
        StatusOS.AGUARDANDO_EXECUCAO,
    )
    assert (registro.origem, registro.usuario_id) == (OrigemTransicao.SISTEMA, None)
    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (3, 0)
    assert eventos == []


async def test_com_reposicao_para_uma_so_das_duas_os_pendentes_a_mais_antiga_recebe(
    alocar, ordens, estoques
):
    peca_id = uuid4()
    await _estoque(estoques, peca_id, fisica=2)
    mais_nova = await _os(ordens, [_item(peca_id, 2)], dias_depois=1)
    mais_antiga = await _os(ordens, [_item(peca_id, 2)])

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, mais_antiga.id, peca_id) == (StatusOS.AGUARDANDO_EXECUCAO, 2, 0)
    assert await _situacao(ordens, mais_nova.id, peca_id) == (StatusOS.AGUARDANDO_PECA, 0, 2)


async def test_o_saldo_passa_de_uma_os_para_a_seguinte_e_para_na_que_ficou_incompleta(
    alocar, ordens, estoques
):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=5)
    primeira = await _os(ordens, [_item(peca_id, 2)])
    segunda = await _os(ordens, [_item(peca_id, 2)], dias_depois=1)
    terceira = await _os(ordens, [_item(peca_id, 2)], dias_depois=2)

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, primeira.id, peca_id) == (StatusOS.AGUARDANDO_EXECUCAO, 2, 0)
    assert await _situacao(ordens, segunda.id, peca_id) == (StatusOS.AGUARDANDO_EXECUCAO, 2, 0)
    assert await _situacao(ordens, terceira.id, peca_id) == (StatusOS.AGUARDANDO_PECA, 1, 1)
    assert estoque.saldo_disponivel() == 0


async def test_os_que_ainda_tem_pendencia_continua_aguardando_a_peca(alocar, ordens, estoques):
    peca_id = uuid4()
    await _estoque(estoques, peca_id, fisica=1)
    os = await _os(ordens, [_item(peca_id, 4)])

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, os.id, peca_id) == (StatusOS.AGUARDANDO_PECA, 1, 3)
    assert len((await ordens.buscar_por_id(os.id)).historico) == 0


async def test_os_com_outra_peca_pendente_nao_e_liberada(alocar, ordens, estoques):
    reposta, faltando = uuid4(), uuid4()
    await _estoque(estoques, reposta, fisica=2)
    os = await _os(ordens, [_item(reposta, 2), _item(faltando, 1)])

    await alocar.tratar(_evento(reposta))

    assert await _situacao(ordens, os.id, reposta) == (StatusOS.AGUARDANDO_PECA, 2, 0)
    assert await _situacao(ordens, os.id, faltando) == (StatusOS.AGUARDANDO_PECA, 0, 1)


async def test_os_aguardando_a_aprovacao_recebe_a_reserva_sem_mudar_o_status(
    alocar, ordens, estoques
):
    peca_id = uuid4()
    await _estoque(estoques, peca_id, fisica=2)
    os = await _os(ordens, [_item(peca_id, 2)], status=StatusOS.AGUARDANDO_APROVACAO)

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, os.id, peca_id) == (StatusOS.AGUARDANDO_APROVACAO, 2, 0)


async def test_usa_o_saldo_atual_do_estoque_e_nao_o_do_evento(alocar, ordens, estoques):
    peca_id = uuid4()
    await _estoque(estoques, peca_id, fisica=3)
    os = await _os(ordens, [_item(peca_id, 3)])

    await alocar.tratar(_evento(peca_id, saldo=0))

    assert await _situacao(ordens, os.id, peca_id) == (StatusOS.AGUARDANDO_EXECUCAO, 3, 0)


async def test_sem_saldo_nada_muda(alocar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=2, reservada=2)
    os = await _os(ordens, [_item(peca_id, 3)])

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, os.id, peca_id) == (StatusOS.AGUARDANDO_PECA, 0, 3)
    assert estoque.quantidade_reservada == 2


async def test_sem_os_pendente_o_estoque_fica_como_esta(alocar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=5)
    await _os(ordens, [_item(peca_id, 2, reservada=2)], status=StatusOS.AGUARDANDO_EXECUCAO)

    await alocar.tratar(_evento(peca_id))

    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (0, 5)


async def test_os_cancelada_nao_recebe_saldo(alocar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=5)
    cancelada = await _os(ordens, [_item(peca_id, 2, reservada=1)], status=StatusOS.CANCELADA)
    cancelada.pecas[0].descartar_pendencia()
    await ordens.salvar(cancelada)

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, cancelada.id, peca_id) == (StatusOS.CANCELADA, 1, 0)
    assert estoque.quantidade_reservada == 0


async def test_tratar_o_mesmo_evento_de_novo_nao_aloca_outra_vez(alocar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=10)
    os = await _os(ordens, [_item(peca_id, 3)])
    await alocar.tratar(_evento(peca_id))

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, os.id, peca_id) == (StatusOS.AGUARDANDO_EXECUCAO, 3, 0)
    assert estoque.quantidade_reservada == 3


async def test_peca_sem_estoque_cadastrado_nao_aloca_nada(alocar, ordens):
    peca_id = uuid4()
    os = await _os(ordens, [_item(peca_id, 2)])

    await alocar.tratar(_evento(peca_id))

    assert await _situacao(ordens, os.id, peca_id) == (StatusOS.AGUARDANDO_PECA, 0, 2)
