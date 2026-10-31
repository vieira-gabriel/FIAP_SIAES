from uuid import UUID, uuid4

import pytest

from application.handlers.estorno_reservas_handler import EstornoReservasHandler
from domain.entities.estoque_peca import EstoquePeca
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
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


def _evento(*estornos: QuantidadePeca) -> OSCanceladaEvent:
    return OSCanceladaEvent(os_id=uuid4(), estornos=list(estornos))


@pytest.fixture
def estornar(estoques) -> EstornoReservasHandler:
    return EstornoReservasHandler(estoques)


async def test_devolve_as_reservas_ao_saldo_disponivel(estornar, estoques):
    peca_id = uuid4()
    estoque = await _estoque(estoques, peca_id, fisica=10, reservada=4)

    await estornar.tratar(_evento(QuantidadePeca(peca_id, 3)))

    assert (estoque.quantidade_reservada, estoque.saldo_disponivel()) == (1, 9)


async def test_estorna_cada_peca_e_devolve_os_eventos_de_saldo(estornar, estoques):
    primeira, segunda = uuid4(), uuid4()
    await _estoque(estoques, primeira, fisica=5, reservada=2)
    await _estoque(estoques, segunda, fisica=5, reservada=1)

    eventos = await estornar.tratar(
        _evento(QuantidadePeca(primeira, 2), QuantidadePeca(segunda, 1))
    )

    assert {type(e) for e in eventos} == {SaldoPecaAtualizadoEvent}
    assert {e.peca_id for e in eventos} == {primeira, segunda}


async def test_sem_estornos_nao_toca_no_estoque(estornar):
    assert await estornar.tratar(_evento()) == []


async def test_bloqueia_os_estoques_em_ordem_de_id():
    estoques = EstoquesQueRegistramOBloqueio()
    menor, maior = sorted((uuid4(), uuid4()))
    await _estoque(estoques, menor, fisica=5, reservada=1)
    await _estoque(estoques, maior, fisica=5, reservada=1)

    await EstornoReservasHandler(estoques).tratar(
        _evento(QuantidadePeca(maior, 1), QuantidadePeca(menor, 1))
    )

    assert estoques.bloqueados == [menor, maior]


async def test_estoque_inexistente_interrompe_o_despacho(estornar):
    with pytest.raises(EntidadeNaoEncontrada):
        await estornar.tratar(_evento(QuantidadePeca(uuid4(), 1)))


async def test_estorno_acima_do_reservado_e_recusado(estornar, estoques):
    peca_id = uuid4()
    await _estoque(estoques, peca_id, fisica=5, reservada=1)

    with pytest.raises(SaldoInsuficiente):
        await estornar.tratar(_evento(QuantidadePeca(peca_id, 2)))
