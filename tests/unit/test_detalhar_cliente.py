from uuid import uuid4

import pytest

from application.use_cases.detalhar_cliente import DetalharCliente
from domain.entities.cliente import Cliente
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.cpf import CPF


def _cliente():
    return Cliente(nome="Maria", documento=CPF("52998224725"), email="m@exemplo.com", telefone="11")


async def test_detalha_cliente_ativo(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)

    assert await DetalharCliente(clientes).executar(cliente.id) == cliente


async def test_cliente_excluido_nao_e_encontrado(clientes):
    cliente = _cliente()
    cliente.excluir()
    await clientes.salvar(cliente)

    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharCliente(clientes).executar(cliente.id)


async def test_cliente_inexistente_nao_e_encontrado(clientes):
    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharCliente(clientes).executar(uuid4())
