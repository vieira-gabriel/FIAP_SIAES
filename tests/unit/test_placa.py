import pytest

from domain.exceptions import PlacaInvalida
from domain.value_objects.placa import Placa


@pytest.mark.parametrize(
    ("digitada", "normalizada"),
    [
        ("ABC1234", "ABC1234"),
        ("ABC1D23", "ABC1D23"),
        ("abc1234", "ABC1234"),
        ("abc1d23", "ABC1D23"),
        ("ABC-1234", "ABC1234"),
        ("abc-1d23", "ABC1D23"),
        (" ABC 1234 ", "ABC1234"),
    ],
)
def test_aceita_os_padroes_antigo_e_mercosul_e_normaliza(digitada, normalizada):
    assert Placa(digitada).valor == normalizada


@pytest.mark.parametrize(
    "invalida",
    [
        "",
        "ABC123",
        "ABC12345",
        "AB1234",
        "ABCD123",
        "1BC1234",
        "ABC12D3",
        "ABC1DD3",
        "ABCD1234",
        "ABC_1234",
        "ABC.1234",
        "ÁBC1234",
    ],
)
def test_recusa_formato_fora_dos_padroes(invalida):
    with pytest.raises(PlacaInvalida) as erro:
        Placa(invalida)

    assert erro.value.placa == invalida


def test_mesma_placa_digitada_de_formas_diferentes_e_igual():
    assert Placa("abc-1d23") == Placa("ABC1D23")
    assert hash(Placa("abc-1d23")) == hash(Placa("ABC1D23"))


def test_e_imutavel():
    placa = Placa("ABC1234")

    with pytest.raises(AttributeError):
        placa.valor = "XYZ9876"
