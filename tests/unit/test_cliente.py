import pytest

from domain.entities.cliente import Cliente
from domain.exceptions import ClienteInvalido, ValorInvalido
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF


def criar_cliente(**alteracoes) -> Cliente:
    dados = {
        "nome": "Maria Silva",
        "documento": CPF("529.982.247-25"),
        "email": "maria@exemplo.com",
        "telefone": "(11) 98765-4321",
    }
    dados.update(alteracoes)
    return Cliente(**dados)


def test_cria_cliente_ativo_com_id():
    cliente = criar_cliente()

    assert cliente.ativo
    assert cliente.id is not None


def test_aceita_pessoa_juridica_com_cnpj():
    cliente = criar_cliente(nome="Oficina Ltda", documento=CNPJ("11.222.333/0001-81"))

    assert cliente.documento == CNPJ("11222333000181")


def test_normaliza_nome_email_e_telefone():
    cliente = criar_cliente(nome="  Maria  ", email=" Maria@Exemplo.COM ", telefone=" 1199 ")

    assert (cliente.nome, cliente.email, cliente.telefone) == ("Maria", "maria@exemplo.com", "1199")


@pytest.mark.parametrize(
    "alteracao",
    [
        {"nome": "   "},
        {"documento": "52998224725"},
        {"email": ""},
        {"email": "sem-arroba"},
        {"telefone": "  "},
    ],
)
def test_rejeita_dados_invalidos(alteracao):
    with pytest.raises(ClienteInvalido) as erro:
        criar_cliente(**alteracao)

    assert isinstance(erro.value, ValorInvalido)


def test_atualizar_dados():
    cliente = criar_cliente()

    cliente.atualizar_dados(
        nome="Maria Souza",
        documento=CPF("111.444.777-35"),
        email="maria.souza@exemplo.com",
        telefone="1133334444",
    )

    assert cliente.nome == "Maria Souza"
    assert cliente.documento == CPF("11144477735")
    assert cliente.email == "maria.souza@exemplo.com"
    assert cliente.telefone == "1133334444"


def test_atualizacao_invalida_nao_altera_nenhum_dado():
    cliente = criar_cliente()

    with pytest.raises(ClienteInvalido):
        cliente.atualizar_dados(
            nome="Outro Nome",
            documento=CPF("111.444.777-35"),
            email="outro@exemplo.com",
            telefone="",
        )

    assert cliente.nome == "Maria Silva"
    assert cliente.documento == CPF("52998224725")
    assert cliente.email == "maria@exemplo.com"


def test_exclusao_logica_mantem_os_dados():
    cliente = criar_cliente()

    cliente.excluir()

    assert not cliente.ativo
    assert cliente.nome == "Maria Silva"


def test_igualdade_pela_identidade():
    cliente = criar_cliente()

    assert cliente != criar_cliente()
    assert cliente == criar_cliente(id=cliente.id, nome="Outro Nome")
    assert len({cliente, criar_cliente()}) == 2
