from uuid import uuid4

import pytest

from application.use_cases.cadastrar_veiculo import CadastrarVeiculo
from domain.entities.cliente import Cliente
from domain.exceptions import EntidadeNaoEncontrada, PlacaJaCadastrada, VeiculoInvalido
from domain.value_objects.cpf import CPF
from domain.value_objects.placa import Placa


@pytest.fixture
async def maria(clientes):
    cliente = Cliente(
        nome="Maria", documento=CPF("52998224725"), email="m@exemplo.com", telefone="11"
    )
    await clientes.salvar(cliente)
    return cliente


@pytest.fixture
def cadastrar(veiculos, clientes):
    return CadastrarVeiculo(veiculos=veiculos, clientes=clientes)


async def test_cadastra_veiculo_vinculado_ao_cliente(cadastrar, veiculos, maria):
    veiculo = await cadastrar.executar(maria.id, Placa("abc-1d23"), "Fiat", "Uno", 2015)

    assert await veiculos.buscar_por_id(veiculo.id) == veiculo
    assert veiculo.cliente_id == maria.id
    assert veiculo.placa == Placa("ABC1D23")
    assert veiculo.ativo


async def test_recusa_cliente_inexistente(cadastrar, veiculos):
    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await cadastrar.executar(uuid4(), Placa("ABC1D23"), "Fiat", "Uno", 2015)

    assert erro.value.entidade == "Cliente"
    assert veiculos.dados == {}


async def test_recusa_cliente_excluido(cadastrar, veiculos, maria):
    maria.excluir()

    with pytest.raises(EntidadeNaoEncontrada):
        await cadastrar.executar(maria.id, Placa("ABC1D23"), "Fiat", "Uno", 2015)

    assert veiculos.dados == {}


async def test_recusa_placa_de_outro_veiculo_ativo(cadastrar, veiculos, maria):
    await cadastrar.executar(maria.id, Placa("ABC1D23"), "Fiat", "Uno", 2015)

    with pytest.raises(PlacaJaCadastrada):
        await cadastrar.executar(maria.id, Placa("abc1d23"), "VW", "Gol", 2018)

    assert len(veiculos.dados) == 1


async def test_placa_de_veiculo_excluido_pode_ser_recadastrada(cadastrar, veiculos, maria):
    vendido = await cadastrar.executar(maria.id, Placa("ABC1D23"), "Fiat", "Uno", 2015)
    vendido.excluir()

    novo = await cadastrar.executar(maria.id, Placa("ABC1D23"), "Fiat", "Uno", 2015)

    assert novo.id != vendido.id
    assert len(veiculos.dados) == 2


async def test_dados_invalidos_nao_gravam_nada(cadastrar, veiculos, maria):
    with pytest.raises(VeiculoInvalido):
        await cadastrar.executar(maria.id, Placa("ABC1D23"), "", "Uno", 2015)

    assert veiculos.dados == {}
