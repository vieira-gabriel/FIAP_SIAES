"""Nenhuma sequência de operações deixa o saldo negativo (RF-12).

As sequências são sorteadas com semente fixa, para o teste ser reproduzível, e misturam
quantidades válidas e inválidas. A cada passo o teste confere as regras do agregado.
"""

import random
from collections import Counter
from uuid import uuid4

from domain.entities.estoque_peca import EstoquePeca
from domain.exceptions import ErroDeDominio

SEMENTE = 20261027
SEQUENCIAS = 2000
PASSOS_POR_SEQUENCIA = 60
QUANTIDADES_INVALIDAS = [-3, 1.5, "2", None, True]
OPERACOES = ["reservar", "baixar", "estornar", "repor", "ajustar_quantidade_fisica"]


def _quantidade_sorteada(sorteio: random.Random):
    if sorteio.random() < 0.1:
        return sorteio.choice(QUANTIDADES_INVALIDAS)
    return sorteio.randint(0, 12)


def _estoque_inicial(sorteio: random.Random) -> EstoquePeca:
    fisica = sorteio.randint(0, 15)
    return EstoquePeca(
        peca_id=uuid4(),
        quantidade_fisica=fisica,
        quantidade_reservada=sorteio.randint(0, fisica),
    )


def _estado(estoque: EstoquePeca) -> tuple[int, int]:
    return estoque.quantidade_fisica, estoque.quantidade_reservada


def _conferir_invariantes(estoque: EstoquePeca) -> None:
    fisica, reservada = _estado(estoque)
    assert type(fisica) is int and type(reservada) is int
    assert 0 <= reservada <= fisica
    assert estoque.saldo_disponivel() >= 0


def test_nenhuma_sequencia_de_operacoes_deixa_o_saldo_negativo():
    sorteio = random.Random(SEMENTE)
    resultados = Counter()

    for _ in range(SEQUENCIAS):
        estoque = _estoque_inicial(sorteio)
        _conferir_invariantes(estoque)
        for _ in range(PASSOS_POR_SEQUENCIA):
            nome = sorteio.choice(OPERACOES)
            quantidade = _quantidade_sorteada(sorteio)
            estado_antes, saldo_antes = _estado(estoque), estoque.saldo_disponivel()

            try:
                retorno = getattr(estoque, nome)(quantidade)
            except ErroDeDominio:
                resultados[nome, "recusada"] += 1
                assert _estado(estoque) == estado_antes
                assert estoque.collect_domain_events() == []
                _conferir_invariantes(estoque)
                continue

            resultados[nome, "aceita"] += 1
            _conferir_invariantes(estoque)
            _conferir_efeito(estoque, nome, quantidade, estado_antes, retorno)
            eventos = estoque.collect_domain_events()
            saldo_aumentou = estoque.saldo_disponivel() > saldo_antes
            assert len(eventos) == (1 if saldo_aumentou else 0)
            if eventos:
                assert eventos[0].saldo_disponivel == estoque.saldo_disponivel()
                assert eventos[0].peca_id == estoque.peca_id

    for nome in OPERACOES:
        assert resultados[nome, "aceita"] > 0, f"{nome} nunca foi aceita no sorteio"
        assert resultados[nome, "recusada"] > 0, f"{nome} nunca foi recusada no sorteio"


def _conferir_efeito(estoque, nome, quantidade, estado_antes, retorno) -> None:
    fisica_antes, reservada_antes = estado_antes
    if nome == "reservar":
        reservada, pendente = retorno
        assert reservada + pendente == quantidade
        assert reservada == min(quantidade, fisica_antes - reservada_antes)
        assert _estado(estoque) == (fisica_antes, reservada_antes + reservada)
    elif nome == "baixar":
        assert _estado(estoque) == (fisica_antes - quantidade, reservada_antes - quantidade)
    elif nome == "estornar":
        assert _estado(estoque) == (fisica_antes, reservada_antes - quantidade)
    elif nome == "repor":
        assert _estado(estoque) == (fisica_antes + quantidade, reservada_antes)
    else:
        assert _estado(estoque) == (quantidade, reservada_antes)
