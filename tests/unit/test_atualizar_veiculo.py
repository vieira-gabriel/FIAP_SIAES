from uuid import uuid4

import pytest

from application.use_cases.atualizar_veiculo import AtualizarVeiculo
from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada, PlacaJaCadastrada
from domain.value_objects.placa import Placa


def _veiculo(placa="ABC1D23"):
    return Veiculo(cliente_id=uuid4(), placa=Placa(placa), marca="Fiat", modelo="Uno", ano=2015)


async def test_atualiza_os_dados_e_mantem_o_proprietario(veiculos):
    veiculo = _veiculo()
    await veiculos.salvar(veiculo)
    proprietario = veiculo.cliente_id

    atualizado = await AtualizarVeiculo(veiculos).executar(
        veiculo.id, Placa("XYZ9876"), "VW", "Gol", 2018
    )

    assert (atualizado.placa, atualizado.marca, atualizado.modelo, atualizado.ano) == (
        Placa("XYZ9876"),
        "VW",
        "Gol",
        2018,
    )
    assert atualizado.cliente_id == proprietario
    assert await veiculos.buscar_por_placa(Placa("XYZ9876")) == veiculo


async def test_manter_a_propria_placa_e_permitido(veiculos):
    veiculo = _veiculo()
    await veiculos.salvar(veiculo)

    atualizado = await AtualizarVeiculo(veiculos).executar(
        veiculo.id, Placa("abc-1d23"), "Fiat", "Uno Way", 2015
    )

    assert atualizado.modelo == "Uno Way"


async def test_recusa_placa_de_outro_veiculo_ativo(veiculos):
    outro = _veiculo(placa="XYZ9876")
    veiculo = _veiculo()
    await veiculos.salvar(outro)
    await veiculos.salvar(veiculo)

    with pytest.raises(PlacaJaCadastrada):
        await AtualizarVeiculo(veiculos).executar(veiculo.id, Placa("XYZ9876"), "Fiat", "Uno", 2015)


async def test_veiculo_excluido_nao_e_encontrado(veiculos):
    veiculo = _veiculo()
    veiculo.excluir()
    await veiculos.salvar(veiculo)

    with pytest.raises(EntidadeNaoEncontrada):
        await AtualizarVeiculo(veiculos).executar(veiculo.id, Placa("ABC1D23"), "Fiat", "Uno", 2015)


async def test_veiculo_inexistente_nao_e_encontrado(veiculos):
    with pytest.raises(EntidadeNaoEncontrada):
        await AtualizarVeiculo(veiculos).executar(uuid4(), Placa("ABC1D23"), "Fiat", "Uno", 2015)
