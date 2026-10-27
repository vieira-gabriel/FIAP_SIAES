"""A alocação respeita a prioridade pela OS mais antiga e nunca passa do saldo (RF-18, RF-19).

Os sorteios usam semente fixa, para o teste ser reproduzível. As datas se repetem de propósito,
para exercitar o empate. As propriedades não repetem o algoritmo: partem do que o resultado
precisa garantir, qualquer que seja a entrada.
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from domain.entities.estoque_peca import EstoquePeca
from domain.value_objects.pendencia_peca import PendenciaPeca

SEMENTE = 20261028
SORTEIOS = 3000
PRIMEIRA_ABERTURA = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def _estoque_sorteado(sorteio: random.Random) -> EstoquePeca:
    fisica = sorteio.randint(0, 20)
    return EstoquePeca(
        peca_id=uuid4(),
        quantidade_fisica=fisica,
        quantidade_reservada=sorteio.randint(0, fisica),
    )


def _pendencias_sorteadas(sorteio: random.Random) -> list[PendenciaPeca]:
    return [
        PendenciaPeca(
            os_id=uuid4(),
            data_abertura_os=PRIMEIRA_ABERTURA + timedelta(days=sorteio.randint(0, 5)),
            quantidade_pendente=sorteio.randint(1, 8),
        )
        for _ in range(sorteio.randint(0, 6))
    ]


def test_a_alocacao_respeita_a_prioridade_e_o_saldo_em_qualquer_entrada():
    sorteio = random.Random(SEMENTE)
    sorteios_com_alocacao = sorteios_com_sobra_de_pendencia = 0

    for _ in range(SORTEIOS):
        estoque = _estoque_sorteado(sorteio)
        pendencias = _pendencias_sorteadas(sorteio)
        sorteio.shuffle(pendencias)
        fisica, reservada_antes = estoque.quantidade_fisica, estoque.quantidade_reservada
        saldo_antes = estoque.saldo_disponivel()

        alocacoes = estoque.alocar_pendencias(pendencias)

        alocado = sum(a.quantidade_reservada for a in alocacoes)
        assert alocado <= saldo_antes
        assert estoque.quantidade_fisica == fisica
        assert estoque.quantidade_reservada == reservada_antes + alocado
        assert 0 <= estoque.quantidade_reservada <= estoque.quantidade_fisica
        assert estoque.collect_domain_events() == []

        pedido = {p.os_id: p.quantidade_pendente for p in pendencias}
        assert len({a.os_id for a in alocacoes}) == len(alocacoes)
        assert all(0 < a.quantidade_reservada <= pedido[a.os_id] for a in alocacoes)

        # A prioridade: a entrega sai na ordem da data de abertura (empate: ordem recebida).
        prioridade = [
            p.os_id
            for _, p in sorted(enumerate(pendencias), key=lambda t: (t[1].data_abertura_os, t[0]))
        ]
        recebido = {a.os_id: a.quantidade_reservada for a in alocacoes}
        assert [a.os_id for a in alocacoes] == [o for o in prioridade if o in recebido]

        # Se uma OS mais nova recebeu peça, todas as mais antigas receberam tudo o que pediram.
        for i, mais_antiga in enumerate(prioridade):
            if any(recebido.get(mais_nova, 0) > 0 for mais_nova in prioridade[i + 1 :]):
                assert recebido.get(mais_antiga, 0) == pedido[mais_antiga]

        # Sem desperdício: ou todas foram atendidas por inteiro, ou o saldo acabou.
        todas_atendidas = all(recebido.get(o, 0) == pedido[o] for o in pedido)
        assert todas_atendidas or estoque.saldo_disponivel() == 0

        sorteios_com_alocacao += bool(alocacoes)
        sorteios_com_sobra_de_pendencia += not todas_atendidas

    assert sorteios_com_alocacao > SORTEIOS // 4, "poucos sorteios chegaram a alocar"
    assert sorteios_com_sobra_de_pendencia > SORTEIOS // 10, "poucos sorteios faltaram saldo"
