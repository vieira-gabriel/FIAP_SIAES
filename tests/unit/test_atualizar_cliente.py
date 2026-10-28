from uuid import uuid4

import pytest

from application.use_cases.atualizar_cliente import AtualizarCliente
from domain.entities.cliente import Cliente
from domain.exceptions import ClienteInvalido, DocumentoJaCadastrado, EntidadeNaoEncontrada
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF


def _cliente(nome="Maria Silva", documento="52998224725"):
    return Cliente(
        nome=nome, documento=CPF(documento), email="maria@exemplo.com", telefone="11987654321"
    )


async def test_atualiza_os_dados_do_cliente(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)

    atualizado = await AtualizarCliente(clientes).executar(
        cliente.id, "Maria Souza", CNPJ("11222333000181"), "novo@exemplo.com", "1133334444"
    )

    assert atualizado.id == cliente.id
    salvo = await clientes.buscar_por_id(cliente.id)
    assert (salvo.nome, salvo.documento, salvo.email, salvo.telefone) == (
        "Maria Souza",
        CNPJ("11222333000181"),
        "novo@exemplo.com",
        "1133334444",
    )


async def test_manter_o_proprio_documento_e_permitido(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)

    atualizado = await AtualizarCliente(clientes).executar(
        cliente.id, "Maria Souza", CPF("529.982.247-25"), "maria@exemplo.com", "11"
    )

    assert atualizado.nome == "Maria Souza"


async def test_recusa_documento_de_outro_cliente(clientes):
    maria = _cliente()
    joao = _cliente(nome="Joao", documento="11144477735")
    await clientes.salvar(maria)
    await clientes.salvar(joao)

    with pytest.raises(DocumentoJaCadastrado):
        await AtualizarCliente(clientes).executar(
            joao.id, "Joao", CPF("52998224725"), "joao@exemplo.com", "11"
        )


async def test_cliente_excluido_nao_e_encontrado(clientes):
    cliente = _cliente()
    cliente.excluir()
    await clientes.salvar(cliente)

    with pytest.raises(EntidadeNaoEncontrada):
        await AtualizarCliente(clientes).executar(
            cliente.id, "Maria", CPF("52998224725"), "maria@exemplo.com", "11"
        )


async def test_cliente_inexistente_nao_e_encontrado(clientes):
    with pytest.raises(EntidadeNaoEncontrada):
        await AtualizarCliente(clientes).executar(
            uuid4(), "Maria", CPF("52998224725"), "maria@exemplo.com", "11"
        )


async def test_dados_invalidos_nao_alteram_o_cliente_salvo(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)
    salvo_antes = await clientes.buscar_por_id(cliente.id)
    email_antes = salvo_antes.email

    with pytest.raises(ClienteInvalido):
        await AtualizarCliente(clientes).executar(
            cliente.id, "Maria", CPF("52998224725"), "sem-arroba", "11"
        )

    assert (await clientes.buscar_por_id(cliente.id)).email == email_antes
