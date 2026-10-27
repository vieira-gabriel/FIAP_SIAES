from uuid import uuid4

import pytest

from domain.entities.estoque_peca import EstoquePeca
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.exceptions import (
    PecaInvalida,
    QuantidadeInvalida,
    SaldoInsuficiente,
    ValorInvalido,
)

QUANTIDADES_NAO_POSITIVAS_OU_NAO_INTEIRAS = [0, -1, 1.5, "2", True, None]


def criar_estoque(fisica: int = 10, reservada: int = 0) -> EstoquePeca:
    return EstoquePeca(peca_id=uuid4(), quantidade_fisica=fisica, quantidade_reservada=reservada)


def test_cria_o_estoque_zerado_e_sem_eventos():
    estoque = EstoquePeca(peca_id=uuid4())

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (0, 0)
    assert estoque.saldo_disponivel() == 0
    assert estoque.collect_domain_events() == []


def test_saldo_disponivel_e_a_quantidade_fisica_menos_a_reservada():
    assert criar_estoque(fisica=10, reservada=3).saldo_disponivel() == 7


@pytest.mark.parametrize(
    "alteracao",
    [
        {"quantidade_fisica": -1},
        {"quantidade_fisica": 1.5},
        {"quantidade_reservada": -1},
        {"quantidade_reservada": "1"},
        {"quantidade_fisica": 2, "quantidade_reservada": 3},
    ],
)
def test_recusa_quantidades_invalidas_na_criacao(alteracao):
    with pytest.raises(QuantidadeInvalida) as erro:
        EstoquePeca(peca_id=uuid4(), **alteracao)

    assert isinstance(erro.value, ValorInvalido)


def test_recusa_estoque_sem_peca():
    with pytest.raises(PecaInvalida):
        EstoquePeca(peca_id="nao-e-uuid")


def test_reserva_total_quando_ha_saldo_para_o_pedido():
    estoque = criar_estoque(fisica=10)

    reservada, pendente = estoque.reservar(4)

    assert (reservada, pendente) == (4, 0)
    assert estoque.quantidade_reservada == 4
    assert estoque.saldo_disponivel() == 6


def test_reserva_parcial_reserva_o_saldo_e_devolve_o_resto_como_pendente():
    estoque = criar_estoque(fisica=10, reservada=7)

    reservada, pendente = estoque.reservar(5)

    assert (reservada, pendente) == (3, 2)
    assert estoque.quantidade_reservada == 10
    assert estoque.saldo_disponivel() == 0


def test_reserva_com_saldo_zero_deixa_todo_o_pedido_pendente():
    estoque = criar_estoque(fisica=5, reservada=5)

    reservada, pendente = estoque.reservar(3)

    assert (reservada, pendente) == (0, 3)
    assert estoque.quantidade_reservada == 5


def test_reserva_em_estoque_vazio_deixa_todo_o_pedido_pendente():
    assert EstoquePeca(peca_id=uuid4()).reservar(2) == (0, 2)


def test_reservar_nao_aumenta_o_saldo_e_nao_emite_evento():
    estoque = criar_estoque()

    estoque.reservar(4)

    assert estoque.collect_domain_events() == []


def test_baixa_reduz_a_quantidade_fisica_e_a_reservada_sem_mudar_o_saldo():
    estoque = criar_estoque(fisica=10, reservada=6)

    estoque.baixar(4)

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (6, 2)
    assert estoque.saldo_disponivel() == 4
    assert estoque.collect_domain_events() == []


def test_baixa_acima_da_quantidade_reservada_e_recusada_sem_alterar_nada():
    estoque = criar_estoque(fisica=10, reservada=3)

    with pytest.raises(SaldoInsuficiente) as erro:
        estoque.baixar(4)

    assert (erro.value.quantidade_solicitada, erro.value.saldo_disponivel) == (4, 3)
    assert str(estoque.peca_id) in str(erro.value)
    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (10, 3)


def test_estorno_devolve_a_reserva_ao_saldo_e_acumula_o_evento():
    estoque = criar_estoque(fisica=10, reservada=6)

    estoque.estornar(4)

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (10, 2)
    assert estoque.saldo_disponivel() == 8
    (evento,) = estoque.collect_domain_events()
    assert isinstance(evento, SaldoPecaAtualizadoEvent)
    assert (evento.peca_id, evento.saldo_disponivel) == (estoque.peca_id, 8)


def test_estorno_acima_da_quantidade_reservada_e_recusado_sem_alterar_nada():
    estoque = criar_estoque(fisica=10, reservada=3)

    with pytest.raises(SaldoInsuficiente):
        estoque.estornar(4)

    assert estoque.quantidade_reservada == 3
    assert estoque.collect_domain_events() == []


def test_reposicao_aumenta_a_quantidade_fisica_e_acumula_o_evento():
    estoque = criar_estoque(fisica=10, reservada=4)

    estoque.repor(5)

    assert estoque.quantidade_fisica == 15
    assert estoque.saldo_disponivel() == 11
    (evento,) = estoque.collect_domain_events()
    assert evento.saldo_disponivel == 11


def test_ajuste_para_cima_aumenta_o_saldo_e_acumula_o_evento():
    estoque = criar_estoque(fisica=10, reservada=4)

    estoque.ajustar_quantidade_fisica(14)

    assert estoque.quantidade_fisica == 14
    (evento,) = estoque.collect_domain_events()
    assert (evento.peca_id, evento.saldo_disponivel) == (estoque.peca_id, 10)


@pytest.mark.parametrize("nova", [8, 4, 10])
def test_ajuste_para_baixo_ou_igual_nao_acumula_evento(nova):
    estoque = criar_estoque(fisica=10, reservada=4)

    estoque.ajustar_quantidade_fisica(nova)

    assert estoque.quantidade_fisica == nova
    assert estoque.collect_domain_events() == []


def test_ajuste_abaixo_da_quantidade_reservada_e_recusado_sem_alterar_nada():
    estoque = criar_estoque(fisica=10, reservada=4)

    with pytest.raises(SaldoInsuficiente) as erro:
        estoque.ajustar_quantidade_fisica(3)

    assert (erro.value.quantidade_solicitada, erro.value.saldo_disponivel) == (4, 3)
    assert estoque.quantidade_fisica == 10
    assert estoque.collect_domain_events() == []


def test_ajuste_para_zero_e_aceito_sem_reservas_e_recusado_com_reservas():
    sem_reservas = criar_estoque(fisica=10, reservada=0)
    com_reservas = criar_estoque(fisica=10, reservada=1)

    sem_reservas.ajustar_quantidade_fisica(0)

    assert sem_reservas.quantidade_fisica == 0
    with pytest.raises(SaldoInsuficiente):
        com_reservas.ajustar_quantidade_fisica(0)


@pytest.mark.parametrize("quantidade", QUANTIDADES_NAO_POSITIVAS_OU_NAO_INTEIRAS)
def test_reservar_baixar_estornar_e_repor_recusam_quantidade_invalida(quantidade):
    estoque = criar_estoque(fisica=10, reservada=5)

    for operacao in (estoque.reservar, estoque.baixar, estoque.estornar, estoque.repor):
        with pytest.raises(QuantidadeInvalida):
            operacao(quantidade)

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (10, 5)
    assert estoque.collect_domain_events() == []


@pytest.mark.parametrize("quantidade", [-1, 1.5, "2", True, None])
def test_ajustar_recusa_quantidade_invalida(quantidade):
    estoque = criar_estoque()

    with pytest.raises(QuantidadeInvalida):
        estoque.ajustar_quantidade_fisica(quantidade)

    assert estoque.quantidade_fisica == 10


def test_collect_domain_events_devolve_na_ordem_e_esvazia_a_lista():
    estoque = criar_estoque(fisica=10, reservada=6)
    estoque.estornar(1)
    estoque.repor(2)

    eventos = estoque.collect_domain_events()

    assert [e.saldo_disponivel for e in eventos] == [5, 7]
    assert estoque.collect_domain_events() == []


def test_igualdade_pela_peca():
    estoque = criar_estoque()
    mesma_peca = EstoquePeca(peca_id=estoque.peca_id, quantidade_fisica=99)

    assert estoque == mesma_peca
    assert estoque != criar_estoque()
    assert len({estoque, mesma_peca}) == 1
