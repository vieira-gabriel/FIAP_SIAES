from decimal import Decimal

import pytest

from domain.exceptions import ValorInvalido
from domain.value_objects.valor import Valor


def test_soma_sem_erro_de_ponto_flutuante():
    assert Valor("0.10") + Valor("0.20") == Valor("0.30")


@pytest.mark.parametrize(
    ("entrada", "quantia"),
    [
        ("10", Decimal("10.00")),
        ("10.5", Decimal("10.50")),
        (Decimal("99.99"), Decimal("99.99")),
        (150, Decimal("150.00")),
        ("0", Decimal("0.00")),
        ("-0", Decimal("0.00")),
    ],
)
def test_guarda_com_duas_casas_decimais(entrada, quantia):
    assert str(Valor(entrada).quantia) == str(quantia)


@pytest.mark.parametrize(
    ("entrada", "arredondado"),
    [
        ("0.005", "0.01"),
        ("0.004", "0.00"),
        ("2.675", "2.68"),
        ("2.665", "2.67"),
        ("10.125", "10.13"),
    ],
)
def test_arredonda_meio_centavo_para_cima(entrada, arredondado):
    assert Valor(entrada).quantia == Decimal(arredondado)


@pytest.mark.parametrize("negativo", ["-0.01", "-10", Decimal("-0.004"), -1])
def test_recusa_valor_negativo(negativo):
    with pytest.raises(ValorInvalido):
        Valor(negativo)


@pytest.mark.parametrize("invalido", ["", "abc", "10,50", "NaN", "Infinity"])
def test_recusa_texto_que_nao_e_numero(invalido):
    with pytest.raises(ValorInvalido):
        Valor(invalido)


def test_recusa_float():
    with pytest.raises(TypeError, match="float"):
        Valor(0.1)


@pytest.mark.parametrize("tipo_errado", [None, True, [10]])
def test_recusa_tipo_nao_suportado(tipo_errado):
    with pytest.raises(TypeError):
        Valor(tipo_errado)


def test_multiplica_por_quantidade_inteira_dos_dois_lados():
    assert Valor("25.00") * 3 == Valor("75.00")
    assert 3 * Valor("25.00") == Valor("75.00")


def test_multiplicar_por_zero_resulta_em_zero():
    assert Valor("25.00") * 0 == Valor("0")


def test_multiplicar_por_quantidade_negativa_e_recusado():
    with pytest.raises(ValorInvalido):
        Valor("25.00") * -1


@pytest.mark.parametrize("quantidade", [1.5, Decimal("2"), True, "3"])
def test_recusa_multiplicar_por_quantidade_nao_inteira(quantidade):
    with pytest.raises(TypeError):
        Valor("25.00") * quantidade


def test_recusa_somar_com_numero_que_nao_e_valor():
    with pytest.raises(TypeError):
        Valor("1.00") + Decimal("1.00")


def test_valores_iguais_com_escritas_diferentes_sao_iguais():
    assert Valor("10.5") == Valor(Decimal("10.50"))
    assert hash(Valor("10.5")) == hash(Valor(Decimal("10.50")))


def test_e_imutavel():
    valor = Valor("10.00")

    with pytest.raises(AttributeError):
        valor.quantia = Decimal("20.00")
