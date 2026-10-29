import pytest

from application.use_cases.cadastrar_cliente import CadastrarCliente
from domain.exceptions import ClienteInvalido, DocumentoJaCadastrado
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF


async def test_cadastra_cliente_pessoa_fisica(clientes):
    cliente = await CadastrarCliente(clientes).executar(
        "Maria Silva", CPF("529.982.247-25"), "Maria@Exemplo.com", "11987654321"
    )

    assert await clientes.buscar_por_id(cliente.id) == cliente
    assert cliente.email == "maria@exemplo.com"
    assert cliente.ativo


async def test_cadastra_cliente_pessoa_juridica(clientes):
    cliente = await CadastrarCliente(clientes).executar(
        "Oficina Parceira Ltda", CNPJ("11.222.333/0001-81"), "contato@parceira.com", "1133334444"
    )

    assert await clientes.buscar_por_documento(CNPJ("11222333000181")) == cliente


async def test_recusa_documento_ja_cadastrado(clientes):
    cadastrar = CadastrarCliente(clientes)
    await cadastrar.executar("Maria Silva", CPF("52998224725"), "maria@exemplo.com", "11")

    with pytest.raises(DocumentoJaCadastrado):
        await cadastrar.executar("Outra Maria", CPF("529.982.247-25"), "outra@exemplo.com", "11")

    assert len(clientes.dados) == 1


async def test_recusa_documento_de_cliente_excluido(clientes):
    cadastrar = CadastrarCliente(clientes)
    excluido = await cadastrar.executar("Maria", CPF("52998224725"), "maria@exemplo.com", "11")
    excluido.excluir()

    with pytest.raises(DocumentoJaCadastrado):
        await cadastrar.executar("Maria Nova", CPF("52998224725"), "nova@exemplo.com", "11")


async def test_dados_invalidos_nao_gravam_nada(clientes):
    with pytest.raises(ClienteInvalido):
        await CadastrarCliente(clientes).executar("", CPF("52998224725"), "maria@exemplo.com", "11")

    assert clientes.dados == {}
