from uuid import UUID

import pytest

from domain.exceptions import NumeroOSInvalido, ValorInvalido
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS

OS_ID = UUID("7f3a9c2b-1d4e-4f60-9a8b-0c1d2e3f4a5b")


def test_gera_a_partir_do_cpf_e_do_uuid_da_os():
    numero = NumeroOS.gerar(CPF("529.982.247-25"), OS_ID)

    assert numero.valor == "529-7F3A9C2B"


def test_gera_a_partir_do_cnpj_e_do_uuid_da_os():
    numero = NumeroOS.gerar(CNPJ("04.252.011/0001-10"), OS_ID)

    assert numero.valor == "042-7F3A9C2B"


def test_uuids_diferentes_geram_numeros_diferentes_para_o_mesmo_cliente():
    cpf = CPF("52998224725")
    outro_id = UUID("00000000-0000-4000-8000-000000000000")

    assert NumeroOS.gerar(cpf, OS_ID) != NumeroOS.gerar(cpf, outro_id)


@pytest.mark.parametrize("valido", ["123-7F3A9C2B", "000-00000000", "999-FFFFFFFF"])
def test_aceita_o_formato_do_rf_13(valido):
    assert NumeroOS(valido).valor == valido


@pytest.mark.parametrize(
    "invalido",
    [
        "123-7f3a9c2b",
        "123-7F3a9C2B",
        "1237F3A9C2B",
        "123 7F3A9C2B",
        "12-7F3A9C2B",
        "1234-7F3A9C2B",
        "123-7F3A9C2",
        "123-7F3A9C2BA",
        "123-7G3A9C2B",
        "ABC-7F3A9C2B",
        " 123-7F3A9C2B",
        "",
    ],
)
def test_recusa_minusculas_tamanho_errado_e_falta_de_hifen(invalido):
    with pytest.raises(NumeroOSInvalido) as erro:
        NumeroOS(invalido)

    assert erro.value.numero == invalido
    assert isinstance(erro.value, ValorInvalido)


def test_mesmo_numero_e_igual():
    assert NumeroOS("123-7F3A9C2B") == NumeroOS.gerar(CPF("123.456.789-09"), OS_ID)


def test_e_imutavel():
    numero = NumeroOS("123-7F3A9C2B")

    with pytest.raises(AttributeError):
        numero.valor = "999-FFFFFFFF"
