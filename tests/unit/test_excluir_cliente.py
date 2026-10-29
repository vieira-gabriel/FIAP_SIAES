import pytest

from application.use_cases.excluir_cliente import ExcluirCliente
from domain.entities.cliente import Cliente
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.cpf import CPF


def _cliente():
    return Cliente(nome="Maria", documento=CPF("52998224725"), email="m@exemplo.com", telefone="11")


async def test_exclusao_logica_mantem_o_registro_inativo(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)

    await ExcluirCliente(clientes).executar(cliente.id)

    salvo = await clientes.buscar_por_id(cliente.id)
    assert salvo is not None
    assert not salvo.ativo


async def test_excluir_de_novo_nao_encontra_o_cliente(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)
    await ExcluirCliente(clientes).executar(cliente.id)

    with pytest.raises(EntidadeNaoEncontrada):
        await ExcluirCliente(clientes).executar(cliente.id)
