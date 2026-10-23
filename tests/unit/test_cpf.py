import pytest

from domain.exceptions import CPFInvalido, ValorInvalido
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF


@pytest.mark.parametrize(
    ("digitado", "normalizado"),
    [
        ("52998224725", "52998224725"),
        ("529.982.247-25", "52998224725"),
        ("111.444.777-35", "11144477735"),
        ("123.456.789-09", "12345678909"),
        (" 390.533.447-05 ", "39053344705"),
    ],
)
def test_aceita_cpf_valido_com_e_sem_pontuacao(digitado, normalizado):
    assert CPF(digitado).valor == normalizado


@pytest.mark.parametrize("tamanho_errado", ["", "5299822472", "529982247250", "529.982.247-2"])
def test_recusa_tamanho_diferente_de_11_digitos(tamanho_errado):
    with pytest.raises(CPFInvalido):
        CPF(tamanho_errado)


@pytest.mark.parametrize("repetido", [str(digito) * 11 for digito in range(10)])
def test_recusa_todos_os_digitos_iguais(repetido):
    with pytest.raises(CPFInvalido):
        CPF(repetido)


@pytest.mark.parametrize(
    "digito_errado",
    ["52998224726", "52998224715", "529.982.247-52", "12345678900"],
)
def test_recusa_digito_verificador_incorreto(digito_errado):
    with pytest.raises(CPFInvalido):
        CPF(digito_errado)


@pytest.mark.parametrize("com_letra", ["5299822472A", "529,982,247-25", "529_982_247_25"])
def test_recusa_caracteres_que_nao_sao_digitos_nem_pontuacao(com_letra):
    with pytest.raises(CPFInvalido):
        CPF(com_letra)


def test_recusa_cnpj_valido():
    with pytest.raises(CPFInvalido):
        CPF("11.222.333/0001-81")


def test_erro_e_de_valor_invalido_e_nao_expoe_o_numero():
    with pytest.raises(ValorInvalido) as erro:
        CPF("52998224726")

    assert "52998224726" not in str(erro.value)


def test_tres_primeiros_digitos():
    assert CPF("529.982.247-25").tres_primeiros_digitos() == "529"


def test_mesmo_cpf_com_e_sem_pontuacao_e_igual():
    assert CPF("529.982.247-25") == CPF("52998224725")
    assert hash(CPF("529.982.247-25")) == hash(CPF("52998224725"))


def test_cpf_nunca_e_igual_a_cnpj():
    assert CPF("52998224725") != CNPJ("11222333000181")


def test_e_imutavel():
    cpf = CPF("52998224725")

    with pytest.raises(AttributeError):
        cpf.valor = "11144477735"
