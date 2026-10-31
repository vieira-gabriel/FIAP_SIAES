from uuid import UUID, uuid4

import pytest

from application.handlers.baixa_estoque_handler import BaixaEstoqueHandler
from domain.entities.estoque_peca import EstoquePeca
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.exceptions import EntidadeNaoEncontrada, SaldoInsuficiente
from domain.repositories.estoque_repository import EstoqueRepository
from domain.value_objects.quantidade_peca import QuantidadePeca


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


async def _estoque(estoques, peca_id: UUID, fisica: int, reservada: int) -> EstoquePeca:
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=fisica, quantidade_reservada=reservada)
    await estoques.salvar(estoque)
    return estoque


def _evento(*baixas: QuantidadePeca) -> ExecucaoIniciadaEvent:
    return ExecucaoIniciadaEvent(os_id=uuid4(), baixas=list(baixas))


@pytest.fixture
def baixar(estoques) -> BaixaEstoqueHandler:
    return BaixaEstoqueHandler(estoques)


async def test_reduz_a_quantidade_fisica_e_a_reservada_sem_mexer_no_saldo(baixar, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=10, reservada=4)
    saldo_antes = estoque.saldo_disponivel()

    eventos = await baixar.tratar(_evento(QuantidadePeca(peca_id, 3)))

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (7, 1)
    assert estoque.saldo_disponivel() == saldo_antes
    assert eventos == []


async def test_baixa_cada_peca_da_os(baixar, estoques):
    primeira, segunda = uuid4(), uuid4()
    um = await _estoque(estoques, primeira, fisica=5, reservada=2)
    outro = await _estoque(estoques, segunda, fisica=3, reservada=3)

    await baixar.tratar(_evento(QuantidadePeca(primeira, 2), QuantidadePeca(segunda, 3)))

    assert (um.quantidade_fisica, um.quantidade_reservada) == (3, 0)
    assert (outro.quantidade_fisica, outro.quantidade_reservada) == (0, 0)


async def test_os_sem_pecas_nao_toca_no_estoque(baixar):
    assert await baixar.tratar(_evento()) == []


async def test_bloqueia_os_estoques_em_ordem_de_id():
    estoques = EstoquesQueRegistramOBloqueio()
    menor, maior = sorted((uuid4(), uuid4()))
    await _estoque(estoques, menor, fisica=5, reservada=1)
    await _estoque(estoques, maior, fisica=5, reservada=1)

    await BaixaEstoqueHandler(estoques).tratar(
        _evento(QuantidadePeca(maior, 1), QuantidadePeca(menor, 1))
    )

    assert estoques.bloqueados == [menor, maior]


async def test_estoque_inexistente_interrompe_o_despacho(baixar):
    with pytest.raises(EntidadeNaoEncontrada):
        await baixar.tratar(_evento(QuantidadePeca(uuid4(), 1)))


async def test_baixa_acima_do_reservado_e_recusada(baixar, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=5, reservada=1)

    with pytest.raises(SaldoInsuficiente):
        await baixar.tratar(_evento(QuantidadePeca(peca_id, 2)))

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (5, 1)
