from uuid import uuid4

import pytest

from application.use_cases.excluir_cliente import ExcluirCliente
from domain.entities.cliente import Cliente
from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.cpf import CPF
from domain.value_objects.placa import Placa


def _cliente():
    return Cliente(nome="Maria", documento=CPF("52998224725"), email="m@exemplo.com", telefone="11")


def _veiculo(placa, cliente_id):
    return Veiculo(cliente_id=cliente_id, placa=Placa(placa), marca="Fiat", modelo="Uno", ano=2015)


@pytest.fixture
def excluir(clientes, veiculos):
    return ExcluirCliente(clientes=clientes, veiculos=veiculos)


async def test_exclusao_logica_mantem_o_registro_inativo(excluir, clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)

    await excluir.executar(cliente.id)

    salvo = await clientes.buscar_por_id(cliente.id)
    assert salvo is not None
    assert not salvo.ativo


async def test_excluir_de_novo_nao_encontra_o_cliente(excluir, clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)
    await excluir.executar(cliente.id)

    with pytest.raises(EntidadeNaoEncontrada):
        await excluir.executar(cliente.id)


async def test_exclui_os_veiculos_do_cliente(excluir, clientes, veiculos):
    cliente = _cliente()
    await clientes.salvar(cliente)
    uno, gol = _veiculo("ABC1D23", cliente.id), _veiculo("XYZ9876", cliente.id)
    await veiculos.salvar(uno)
    await veiculos.salvar(gol)

    await excluir.executar(cliente.id)

    assert not uno.ativo
    assert not gol.ativo
    assert await veiculos.listar(cliente.id) == []


async def test_veiculos_de_outros_clientes_continuam_ativos(excluir, clientes, veiculos):
    cliente = _cliente()
    await clientes.salvar(cliente)
    de_outro_cliente = _veiculo("ABC1D23", uuid4())
    await veiculos.salvar(de_outro_cliente)

    await excluir.executar(cliente.id)

    assert de_outro_cliente.ativo
