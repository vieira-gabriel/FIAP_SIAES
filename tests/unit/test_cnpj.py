import pytest

from domain.exceptions import CNPJInvalido, ValorInvalido
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.documento import Documento


@pytest.mark.parametrize(
    ("digitado", "normalizado"),
    [
        ("11222333000181", "11222333000181"),
        ("11.222.333/0001-81", "11222333000181"),
        ("04.252.011/0001-10", "04252011000110"),
        ("45.723.174/0001-10", "45723174000110"),
        (" 33.000.167/0001-01 ", "33000167000101"),
    ],
)
def test_aceita_cnpj_valido_com_e_sem_pontuacao(digitado, normalizado):
    assert CNPJ(digitado).valor == normalizado


@pytest.mark.parametrize(
    "tamanho_errado", ["", "1122233300018", "112223330001810", "11.222.333/0001-8"]
)
def test_recusa_tamanho_diferente_de_14_digitos(tamanho_errado):
    with pytest.raises(CNPJInvalido):
        CNPJ(tamanho_errado)


@pytest.mark.parametrize("repetido", [str(digito) * 14 for digito in range(10)])
def test_recusa_todos_os_digitos_iguais(repetido):
    with pytest.raises(CNPJInvalido):
        CNPJ(repetido)


@pytest.mark.parametrize(
    "digito_errado",
    ["11222333000182", "11222333000191", "11.222.333/0001-18", "04252011000101"],
)
def test_recusa_digito_verificador_incorreto(digito_errado):
    with pytest.raises(CNPJInvalido):
        CNPJ(digito_errado)


@pytest.mark.parametrize(
    "com_letra", ["1122233300018A", "AB.222.333/0001-81", "11,222,333/0001-81"]
)
def test_recusa_caracteres_que_nao_sao_digitos_nem_pontuacao(com_letra):
    with pytest.raises(CNPJInvalido):
        CNPJ(com_letra)


def test_recusa_cpf_valido():
    with pytest.raises(CNPJInvalido):
        CNPJ("529.982.247-25")


def test_erro_e_de_valor_invalido_e_nao_expoe_o_numero():
    with pytest.raises(ValorInvalido) as erro:
        CNPJ("11222333000182")

    assert "11222333000182" not in str(erro.value)


def test_tres_primeiros_digitos():
    assert CNPJ("04.252.011/0001-10").tres_primeiros_digitos() == "042"


def test_mesmo_cnpj_com_e_sem_pontuacao_e_igual():
    assert CNPJ("11.222.333/0001-81") == CNPJ("11222333000181")


def test_e_imutavel():
    cnpj = CNPJ("11222333000181")

    with pytest.raises(AttributeError):
        cnpj.valor = "04252011000110"


def test_documento_nao_pode_ser_criado_diretamente():
    with pytest.raises(TypeError):
        Documento("52998224725")
