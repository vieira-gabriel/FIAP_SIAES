import pytest

from domain.exceptions import CNPJInvalido, CPFInvalido, DocumentoInvalido, ValorInvalido
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF
from domain.value_objects.documento import Documento


@pytest.mark.parametrize(
    ("digitado", "tipo", "valor"),
    [
        ("529.982.247-25", CPF, "52998224725"),
        ("52998224725", CPF, "52998224725"),
        ("11.222.333/0001-81", CNPJ, "11222333000181"),
        ("11222333000181", CNPJ, "11222333000181"),
    ],
)
def test_de_texto_escolhe_cpf_ou_cnpj_pela_quantidade_de_digitos(digitado, tipo, valor):
    documento = Documento.de_texto(digitado)

    assert type(documento) is tipo
    assert documento.valor == valor


@pytest.mark.parametrize("tamanho_errado", ["", "123", "5299822472", "529982247250", "1" * 15])
def test_de_texto_recusa_quantidade_que_nao_e_de_cpf_nem_de_cnpj(tamanho_errado):
    with pytest.raises(DocumentoInvalido) as erro:
        Documento.de_texto(tamanho_errado)

    assert isinstance(erro.value, ValorInvalido)


@pytest.mark.parametrize(
    ("digitado", "excecao"),
    [("529.982.247-26", CPFInvalido), ("11.222.333/0001-82", CNPJInvalido)],
)
def test_de_texto_mantem_a_validacao_dos_digitos_verificadores(digitado, excecao):
    with pytest.raises(excecao):
        Documento.de_texto(digitado)
