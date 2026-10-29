from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.estoque_peca import EstoquePeca
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.exceptions import (
    AlocacaoInvalida,
    PecaInvalida,
    QuantidadeInvalida,
    SaldoInsuficiente,
    ValorInvalido,
)
from domain.value_objects.alocacao_peca import AlocacaoPeca
from domain.value_objects.pendencia_peca import PendenciaPeca

QUANTIDADES_NAO_POSITIVAS_OU_NAO_INTEIRAS = [0, -1, 1.5, "2", True, None]
PRIMEIRA_ABERTURA = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


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


def pendencia(dias_apos_a_primeira: int, quantidade: int) -> PendenciaPeca:
    """Uma OS aberta alguns dias depois da primeira; quanto maior o número, mais nova."""
    return PendenciaPeca(
        os_id=uuid4(),
        data_abertura_os=PRIMEIRA_ABERTURA + timedelta(days=dias_apos_a_primeira),
        quantidade_pendente=quantidade,
    )


def test_reposicao_insuficiente_para_duas_os_atende_a_mais_antiga_primeiro():
    estoque = criar_estoque(fisica=3)
    antiga, nova = pendencia(0, 2), pendencia(5, 2)

    alocacoes = estoque.alocar_pendencias([antiga, nova])

    assert alocacoes == [AlocacaoPeca(antiga.os_id, 2), AlocacaoPeca(nova.os_id, 1)]
    assert estoque.quantidade_reservada == 3
    assert estoque.saldo_disponivel() == 0


def test_a_ordem_recebida_nao_muda_a_prioridade():
    estoque = criar_estoque(fisica=3)
    antiga, nova = pendencia(0, 2), pendencia(5, 2)

    alocacoes = estoque.alocar_pendencias([nova, antiga])

    assert [a.os_id for a in alocacoes] == [antiga.os_id, nova.os_id]
    assert [a.quantidade_reservada for a in alocacoes] == [2, 1]


def test_os_nova_na_conclusao_do_orcamento_so_recebe_o_que_sobra_das_mais_antigas():
    estoque = criar_estoque(fisica=2)
    antiga, nova = pendencia(0, 5), pendencia(9, 1)

    alocacoes = estoque.alocar_pendencias([antiga, nova])

    assert alocacoes == [AlocacaoPeca(antiga.os_id, 2)]
    assert estoque.quantidade_reservada == 2


def test_saldo_suficiente_atende_todas_na_ordem_de_abertura():
    estoque = criar_estoque(fisica=10)
    primeira, segunda, terceira = pendencia(0, 2), pendencia(1, 3), pendencia(2, 4)

    alocacoes = estoque.alocar_pendencias([terceira, primeira, segunda])

    assert alocacoes == [
        AlocacaoPeca(primeira.os_id, 2),
        AlocacaoPeca(segunda.os_id, 3),
        AlocacaoPeca(terceira.os_id, 4),
    ]
    assert estoque.saldo_disponivel() == 1


def test_reservas_existentes_nao_sao_remanejadas():
    estoque = criar_estoque(fisica=10, reservada=6)

    alocacoes = estoque.alocar_pendencias([pendencia(0, 9)])

    assert [a.quantidade_reservada for a in alocacoes] == [4]
    assert estoque.quantidade_reservada == 10
    assert estoque.quantidade_fisica == 10


def test_so_devolve_as_os_que_receberam_alguma_quantidade():
    estoque = criar_estoque(fisica=1)
    antiga, nova = pendencia(0, 4), pendencia(1, 4)

    alocacoes = estoque.alocar_pendencias([antiga, nova])

    assert [a.os_id for a in alocacoes] == [antiga.os_id]


def test_sem_saldo_nao_aloca_nada_e_nao_altera_o_estoque():
    estoque = criar_estoque(fisica=5, reservada=5)

    assert estoque.alocar_pendencias([pendencia(0, 2), pendencia(1, 2)]) == []

    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (5, 5)


def test_sem_pendencias_nao_aloca_nada():
    estoque = criar_estoque()

    assert estoque.alocar_pendencias([]) == []
    assert estoque.quantidade_reservada == 0


def test_empate_na_data_de_abertura_respeita_a_ordem_recebida():
    estoque = criar_estoque(fisica=3)
    primeira, segunda = pendencia(0, 2), pendencia(0, 2)

    alocacoes = estoque.alocar_pendencias([primeira, segunda])

    assert alocacoes == [AlocacaoPeca(primeira.os_id, 2), AlocacaoPeca(segunda.os_id, 1)]


def test_aceita_qualquer_iteravel_de_pendencias():
    estoque = criar_estoque(fisica=5)

    alocacoes = estoque.alocar_pendencias(p for p in [pendencia(0, 2), pendencia(1, 2)])

    assert [a.quantidade_reservada for a in alocacoes] == [2, 2]


def test_alocar_nao_emite_evento_porque_o_saldo_nao_aumenta():
    estoque = criar_estoque(fisica=5)

    estoque.alocar_pendencias([pendencia(0, 2)])

    assert estoque.collect_domain_events() == []


def test_duas_pendencias_da_mesma_os_sao_recusadas_sem_reservar_nada():
    estoque = criar_estoque(fisica=10)
    repetida = pendencia(0, 2)
    outra_da_mesma_os = PendenciaPeca(repetida.os_id, repetida.data_abertura_os, 1)

    with pytest.raises(AlocacaoInvalida):
        estoque.alocar_pendencias([pendencia(1, 3), repetida, outra_da_mesma_os])

    assert estoque.quantidade_reservada == 0


@pytest.mark.parametrize("intruso", ["pendencia", None, 3, (uuid4(), 2)])
def test_pendencia_que_nao_e_do_tipo_certo_e_recusada_sem_reservar_nada(intruso):
    estoque = criar_estoque(fisica=10)

    with pytest.raises(AlocacaoInvalida):
        estoque.alocar_pendencias([pendencia(0, 2), intruso])

    assert estoque.quantidade_reservada == 0


def test_igualdade_pela_peca():
    estoque = criar_estoque()
    mesma_peca = EstoquePeca(peca_id=estoque.peca_id, quantidade_fisica=99)

    assert estoque == mesma_peca
    assert estoque != criar_estoque()
    assert len({estoque, mesma_peca}) == 1
