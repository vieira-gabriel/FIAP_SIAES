from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from domain.exceptions import AlocacaoInvalida, QuantidadeInvalida, ValorInvalido
from domain.value_objects.alocacao_peca import AlocacaoPeca


def test_guarda_a_os_e_a_quantidade_reservada():
    os_id = uuid4()

    alocacao = AlocacaoPeca(os_id=os_id, quantidade_reservada=2)

    assert (alocacao.os_id, alocacao.quantidade_reservada) == (os_id, 2)


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, "2", True, None])
def test_recusa_quantidade_que_nao_e_inteiro_positivo(quantidade):
    with pytest.raises(QuantidadeInvalida) as erro:
        AlocacaoPeca(os_id=uuid4(), quantidade_reservada=quantidade)

    assert isinstance(erro.value, ValorInvalido)


@pytest.mark.parametrize("os_id", ["nao-e-uuid", None, 123])
def test_recusa_os_que_nao_e_uuid(os_id):
    with pytest.raises(AlocacaoInvalida):
        AlocacaoPeca(os_id=os_id, quantidade_reservada=1)


def test_alocacoes_iguais_sao_iguais_e_o_objeto_e_imutavel():
    os_id = uuid4()
    alocacao = AlocacaoPeca(os_id=os_id, quantidade_reservada=2)

    assert alocacao == AlocacaoPeca(os_id=os_id, quantidade_reservada=2)
    assert hash(alocacao) == hash(AlocacaoPeca(os_id=os_id, quantidade_reservada=2))
    with pytest.raises(FrozenInstanceError):
        alocacao.quantidade_reservada = 9
