from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from application.handlers.reserva_pecas_handler import ReservaPecasHandler
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.estoque_repository import EstoqueRepository
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

ABERTURA = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)


class EstoquesQueRegistramOBloqueio(EstoqueRepository):
    def __init__(self):
        self.dados: dict[UUID, EstoquePeca] = {}
        self.bloqueados: list[UUID] = []

    async def salvar(self, estoque):
        self.dados[estoque.peca_id] = estoque

    async def buscar_por_peca(self, peca_id):
        self.bloqueados.append(peca_id)
        return self.dados.get(peca_id)

    async def buscar_por_pecas(self, peca_ids):
        raise NotImplementedError


def _item(peca_id: UUID, quantidade: int, pendente: int | None = None) -> ItemPeca:
    return ItemPeca(
        peca_id=peca_id,
        nome="Filtro de óleo",
        quantidade=quantidade,
        preco_unitario_congelado=Valor("35.90"),
        prazo_reposicao_dias=3,
        quantidade_pendente=quantidade if pendente is None else pendente,
    )


async def _os(
    ordens,
    itens: list[ItemPeca],
    status: StatusOS = StatusOS.AGUARDANDO_APROVACAO,
    abertura: datetime = ABERTURA,
) -> OrdemServico:
    os = OrdemServico(
        numero=NumeroOS.gerar(CPF("529.982.247-25"), uuid4()),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=status,
        data_abertura=abertura,
        pecas=itens,
    )
    await ordens.salvar(os)
    return os


async def _estoque(estoques, peca_id: UUID, fisica: int) -> EstoquePeca:
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=fisica)
    await estoques.salvar(estoque)
    return estoque


def _evento(os: OrdemServico) -> OrcamentoFinalizadoEvent:
    return OrcamentoFinalizadoEvent(os_id=os.id)


@pytest.fixture
def estoques():
    return EstoquesQueRegistramOBloqueio()


@pytest.fixture
def reservar(ordens, estoques) -> ReservaPecasHandler:
    return ReservaPecasHandler(ordens, estoques)


async def _reservada_e_pendente(ordens, os_id, peca_id) -> tuple[int, int]:
    (item,) = [i for i in (await ordens.buscar_por_id(os_id)).pecas if i.peca_id == peca_id]
    return item.quantidade_reservada, item.quantidade_pendente


async def test_reserva_total_quando_o_saldo_cobre_a_quantidade(reservar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=10)
    os = await _os(ordens, [_item(peca_id, 3)])

    eventos = await reservar.tratar(_evento(os))

    assert await _reservada_e_pendente(ordens, os.id, peca_id) == (3, 0)
    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (3, 7)
    assert eventos == []


async def test_reserva_parcial_deixa_o_resto_pendente(reservar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=2)
    os = await _os(ordens, [_item(peca_id, 5)])

    await reservar.tratar(_evento(os))

    assert await _reservada_e_pendente(ordens, os.id, peca_id) == (2, 3)
    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (2, 0)


async def test_saldo_zero_deixa_toda_a_quantidade_pendente(reservar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=0)
    os = await _os(ordens, [_item(peca_id, 4)])

    await reservar.tratar(_evento(os))

    assert await _reservada_e_pendente(ordens, os.id, peca_id) == (0, 4)
    assert estoque.quantidade_reservada == 0
    assert (await ordens.buscar_por_id(os.id)).status is StatusOS.AGUARDANDO_APROVACAO


async def test_reserva_cada_peca_da_os_pelo_proprio_saldo(reservar, ordens, estoques):
    com_saldo, sem_saldo = uuid4(), uuid4()
    await _estoque(estoques, com_saldo, fisica=5)
    await _estoque(estoques, sem_saldo, fisica=1)
    os = await _os(ordens, [_item(com_saldo, 2), _item(sem_saldo, 3)])

    await reservar.tratar(_evento(os))

    assert await _reservada_e_pendente(ordens, os.id, com_saldo) == (2, 0)
    assert await _reservada_e_pendente(ordens, os.id, sem_saldo) == (1, 2)


async def test_bloqueia_o_estoque_de_cada_peca_em_ordem_de_id(reservar, ordens, estoques):
    ids = [uuid4(), uuid4(), uuid4()]
    for peca_id in ids:
        await _estoque(estoques, peca_id, fisica=1)
    os = await _os(ordens, [_item(peca_id, 1) for peca_id in ids])

    await reservar.tratar(_evento(os))

    assert estoques.bloqueados == sorted(ids)


async def test_a_os_mais_antiga_que_espera_a_peca_recebe_o_saldo_primeiro(
    reservar, ordens, estoques
):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=4)
    antiga = await _os(
        ordens,
        [_item(peca_id, 3, pendente=3)],
        status=StatusOS.AGUARDANDO_PECA,
        abertura=ABERTURA - timedelta(days=2),
    )
    nova = await _os(ordens, [_item(peca_id, 3)])

    await reservar.tratar(_evento(nova))

    assert await _reservada_e_pendente(ordens, antiga.id, peca_id) == (3, 0)
    assert (await ordens.buscar_por_id(antiga.id)).status is StatusOS.AGUARDANDO_EXECUCAO
    assert await _reservada_e_pendente(ordens, nova.id, peca_id) == (1, 2)
    assert estoque.saldo_disponivel() == 0


async def test_a_os_nova_nao_usa_o_saldo_que_a_os_mais_antiga_ainda_espera(
    reservar, ordens, estoques
):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=2)
    antiga = await _os(
        ordens,
        [_item(peca_id, 5, pendente=5)],
        status=StatusOS.AGUARDANDO_PECA,
        abertura=ABERTURA - timedelta(days=2),
    )
    nova = await _os(ordens, [_item(peca_id, 3)])

    await reservar.tratar(_evento(nova))

    assert await _reservada_e_pendente(ordens, antiga.id, peca_id) == (2, 3)
    assert await _reservada_e_pendente(ordens, nova.id, peca_id) == (0, 3)
    assert estoque.saldo_disponivel() == 0


async def test_no_empate_de_data_de_abertura_a_os_que_ja_esperava_a_peca_vem_antes(
    reservar, ordens, estoques
):
    peca_id = uuid4()
    await _estoque(estoques, peca_id, fisica=2)
    nova = await _os(ordens, [_item(peca_id, 2)], abertura=ABERTURA)
    esperando = await _os(
        ordens, [_item(peca_id, 2, pendente=2)], status=StatusOS.AGUARDANDO_PECA, abertura=ABERTURA
    )

    await reservar.tratar(_evento(nova))

    assert await _reservada_e_pendente(ordens, esperando.id, peca_id) == (2, 0)
    assert await _reservada_e_pendente(ordens, nova.id, peca_id) == (0, 2)


async def test_os_mais_nova_que_espera_a_peca_nao_passa_na_frente_da_nova(
    reservar, ordens, estoques
):
    peca_id = uuid4()
    await _estoque(estoques, peca_id, fisica=2)
    nova = await _os(ordens, [_item(peca_id, 2)])
    depois = await _os(
        ordens,
        [_item(peca_id, 2, pendente=2)],
        status=StatusOS.AGUARDANDO_PECA,
        abertura=ABERTURA + timedelta(days=1),
    )

    await reservar.tratar(_evento(nova))

    assert await _reservada_e_pendente(ordens, nova.id, peca_id) == (2, 0)
    assert await _reservada_e_pendente(ordens, depois.id, peca_id) == (0, 2)


async def test_tratar_o_mesmo_evento_de_novo_nao_reserva_outra_vez(reservar, ordens, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=10)
    os = await _os(ordens, [_item(peca_id, 3)])
    await reservar.tratar(_evento(os))

    await reservar.tratar(_evento(os))

    assert await _reservada_e_pendente(ordens, os.id, peca_id) == (3, 0)
    assert estoque.quantidade_reservada == 3


async def test_peca_sem_estoque_cadastrado_fica_pendente(reservar, ordens):
    peca_id = uuid4()
    os = await _os(ordens, [_item(peca_id, 2)])

    await reservar.tratar(_evento(os))

    assert await _reservada_e_pendente(ordens, os.id, peca_id) == (0, 2)


async def test_os_sem_pecas_nada_reserva(reservar, ordens, estoques):
    os = await _os(ordens, [])

    assert await reservar.tratar(_evento(os)) == []
    assert estoques.bloqueados == []


async def test_os_inexistente_responde_nao_encontrada(reservar):
    with pytest.raises(EntidadeNaoEncontrada):
        await reservar.tratar(OrcamentoFinalizadoEvent(os_id=uuid4()))
