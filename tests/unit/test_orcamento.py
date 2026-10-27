from decimal import Decimal

import pytest

from domain.value_objects.orcamento import Orcamento
from domain.value_objects.valor import Valor


def test_total_soma_os_subtotais_de_servicos_e_pecas():
    orcamento = Orcamento(subtotal_servicos=Valor("120.00"), subtotal_pecas=Valor("71.80"))

    assert orcamento.total == Valor("191.80")


def test_total_sem_erro_de_ponto_flutuante():
    orcamento = Orcamento(subtotal_servicos=Valor("0.10"), subtotal_pecas=Valor("0.20"))

    assert orcamento.total.valor == Decimal("0.30")


def test_orcamento_so_de_servicos_ou_so_de_pecas():
    so_servicos = Orcamento(subtotal_servicos=Valor("80.00"), subtotal_pecas=Valor("0"))
    so_pecas = Orcamento(subtotal_servicos=Valor("0"), subtotal_pecas=Valor("35.90"))

    assert so_servicos.total == Valor("80.00")
    assert so_pecas.total == Valor("35.90")


@pytest.mark.parametrize("nao_e_valor", ["10.00", 10, Decimal("10.00"), None])
def test_recusa_subtotal_que_nao_e_valor(nao_e_valor):
    with pytest.raises(TypeError):
        Orcamento(subtotal_servicos=nao_e_valor, subtotal_pecas=Valor("1.00"))
    with pytest.raises(TypeError):
        Orcamento(subtotal_servicos=Valor("1.00"), subtotal_pecas=nao_e_valor)


def test_orcamentos_com_os_mesmos_subtotais_sao_iguais():
    um = Orcamento(subtotal_servicos=Valor("10"), subtotal_pecas=Valor("5.5"))
    outro = Orcamento(subtotal_servicos=Valor("10.00"), subtotal_pecas=Valor("5.50"))

    assert um == outro
    assert hash(um) == hash(outro)


def test_total_nao_pode_ser_informado_na_criacao():
    with pytest.raises(TypeError):
        Orcamento(subtotal_servicos=Valor("10"), subtotal_pecas=Valor("5"), total=Valor("1"))


def test_e_imutavel():
    orcamento = Orcamento(subtotal_servicos=Valor("10"), subtotal_pecas=Valor("5"))

    with pytest.raises(AttributeError):
        orcamento.subtotal_pecas = Valor("99")
    with pytest.raises(AttributeError):
        orcamento.total = Valor("99")
