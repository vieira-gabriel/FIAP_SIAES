from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from application.events.event_dispatcher import EventDispatcher
from application.handlers.alocacao_pecas_pendentes_handler import AlocacaoPecasPendentesHandler
from application.handlers.estorno_reservas_handler import EstornoReservasHandler
from application.use_cases.localizar_os_do_titular import LocalizarOSDoTitular
from application.use_cases.rejeitar_orcamento import RejeitarOrcamento
from domain.entities.cliente import Cliente
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.exceptions import EntidadeNaoEncontrada, TransicaoDeStatusInvalida
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

MOMENTO = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
ABERTURA = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
NUMERO = "529-7F3A9C2B"
DOCUMENTO = "529.982.247-25"


@pytest.fixture
def rejeitar(ordens, clientes, estoques) -> RejeitarOrcamento:
    despachador = EventDispatcher()
    despachador.registrar(OSCanceladaEvent, EstornoReservasHandler(estoques))
    despachador.registrar(SaldoPecaAtualizadoEvent, AlocacaoPecasPendentesHandler(ordens, estoques))
    return RejeitarOrcamento(LocalizarOSDoTitular(ordens, clientes), ordens, despachador)


def _peca(peca_id: UUID, quantidade: int, reservada: int) -> ItemPeca:
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
    clientes,
    ordens,
    pecas=(),
    status=StatusOS.AGUARDANDO_APROVACAO,
    numero=NUMERO,
    cliente=None,
    dias_depois=0,
) -> OrdemServico:
    if cliente is None:
        cliente = Cliente(
            nome="Maria", documento=CPF("52998224725"), email="m@e.com", telefone="11"
        )
        await clientes.salvar(cliente)
    os = OrdemServico(
        numero=NumeroOS(numero),
        cliente_id=cliente.id,
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=status,
        data_abertura=ABERTURA + timedelta(days=dias_depois),
        pecas=list(pecas),
    )
    await ordens.salvar(os)
    return os


async def test_rejeicao_cancela_a_os_com_origem_cliente_e_sem_usuario(rejeitar, clientes, ordens):
    os = await _os(clientes, ordens)

    acompanhamento = await rejeitar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert acompanhamento.os is os
    assert os.status is StatusOS.CANCELADA
    assert acompanhamento.estimativa_entrega is None
    registro = os.historico[-1]
    assert (registro.status_anterior, registro.origem, registro.usuario_id) == (
        StatusOS.AGUARDANDO_APROVACAO,
        OrigemTransicao.CLIENTE,
        None,
    )
    assert (await ordens.buscar_por_id(os.id)).status is StatusOS.CANCELADA


async def test_rejeicao_devolve_as_reservas_ao_saldo(rejeitar, clientes, ordens, estoques):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=5, quantidade_reservada=2)
    await estoques.salvar(estoque)
    await _os(clientes, ordens, pecas=[_peca(peca_id, 2, reservada=2)])

    await rejeitar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (0, 5)


async def test_rejeicao_remove_as_pendencias_da_os(rejeitar, clientes, ordens, estoques):
    peca_id = uuid4()
    await estoques.salvar(EstoquePeca(peca_id=peca_id, quantidade_fisica=1, quantidade_reservada=1))
    await _os(clientes, ordens, pecas=[_peca(peca_id, 3, reservada=1)])

    await rejeitar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert await ordens.listar_pendentes_da_peca(peca_id) == []


async def test_saldo_devolvido_libera_a_os_que_esperava_a_peca(
    rejeitar, clientes, ordens, estoques
):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=3, quantidade_reservada=3)
    await estoques.salvar(estoque)
    await _os(clientes, ordens, pecas=[_peca(peca_id, 3, reservada=3)])
    esperando = await _os(
        clientes,
        ordens,
        pecas=[_peca(peca_id, 2, reservada=0)],
        status=StatusOS.AGUARDANDO_PECA,
        numero="111-AAAAAAAA",
        cliente=Cliente(nome="Outro", documento=CPF("11144477735"), email="o@e.com", telefone="11"),
        dias_depois=1,
    )

    await rejeitar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert esperando.status is StatusOS.AGUARDANDO_EXECUCAO
    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (2, 1)


@pytest.mark.parametrize(
    "status",
    [
        StatusOS.RECEBIDA,
        StatusOS.EM_DIAGNOSTICO,
        StatusOS.AGUARDANDO_PECA,
        StatusOS.AGUARDANDO_EXECUCAO,
        StatusOS.EM_EXECUCAO,
        StatusOS.FINALIZADA,
        StatusOS.ENTREGUE,
        StatusOS.CANCELADA,
    ],
)
async def test_rejeicao_fora_de_aguardando_aprovacao_e_recusada(
    rejeitar, clientes, ordens, estoques, status
):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=5, quantidade_reservada=2)
    await estoques.salvar(estoque)
    os = await _os(clientes, ordens, pecas=[_peca(peca_id, 2, reservada=2)], status=status)

    with pytest.raises(TransicaoDeStatusInvalida):
        await rejeitar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert os.status is status
    assert estoque.quantidade_reservada == 2


@pytest.mark.parametrize(
    ("numero", "documento"),
    [("999-00000000", DOCUMENTO), (NUMERO, "111.444.777-35"), (NUMERO, "lixo")],
    ids=["numero inexistente", "documento de outro titular", "documento malformado"],
)
async def test_identificacao_errada_nao_rejeita(
    rejeitar, clientes, ordens, estoques, numero, documento
):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=5, quantidade_reservada=2)
    await estoques.salvar(estoque)
    os = await _os(clientes, ordens, pecas=[_peca(peca_id, 2, reservada=2)])

    with pytest.raises(EntidadeNaoEncontrada):
        await rejeitar.executar(numero, documento, MOMENTO)

    assert os.status is StatusOS.AGUARDANDO_APROVACAO
    assert estoque.quantidade_reservada == 2
