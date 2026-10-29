from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from domain.exceptions import PecaInvalida, QuantidadeInvalida, ValorInvalido
from domain.value_objects.quantidade_peca import QuantidadePeca


def test_guarda_a_peca_e_a_quantidade():
    peca_id = uuid4()

    quantidade = QuantidadePeca(peca_id, 3)

    assert (quantidade.peca_id, quantidade.quantidade) == (peca_id, 3)


def test_e_igual_por_valor():
    peca_id = uuid4()

    assert QuantidadePeca(peca_id, 2) == QuantidadePeca(peca_id, 2)
    assert QuantidadePeca(peca_id, 2) != QuantidadePeca(peca_id, 3)
    assert QuantidadePeca(peca_id, 2) != QuantidadePeca(uuid4(), 2)


def test_e_imutavel():
    quantidade = QuantidadePeca(uuid4(), 1)

    with pytest.raises(FrozenInstanceError):
        quantidade.quantidade = 5


@pytest.mark.parametrize("peca_id", [None, "nao-e-uuid", 123])
def test_recusa_peca_invalida(peca_id):
    with pytest.raises(PecaInvalida) as erro:
        QuantidadePeca(peca_id, 1)

    assert isinstance(erro.value, ValorInvalido)


@pytest.mark.parametrize("quantidade", [0, -1, True, 1.5, "2", None])
def test_recusa_quantidade_que_nao_seja_inteiro_maior_que_zero(quantidade):
    with pytest.raises(QuantidadeInvalida):
        QuantidadePeca(uuid4(), quantidade)
