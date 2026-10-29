from uuid import uuid4

import pytest

from application.use_cases.detalhar_veiculo import DetalharVeiculo
from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.placa import Placa


def _veiculo():
    return Veiculo(cliente_id=uuid4(), placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2015)


async def test_detalha_veiculo_ativo(veiculos):
    veiculo = _veiculo()
    await veiculos.salvar(veiculo)

    assert await DetalharVeiculo(veiculos).executar(veiculo.id) == veiculo


async def test_veiculo_excluido_nao_e_encontrado(veiculos):
    veiculo = _veiculo()
    veiculo.excluir()
    await veiculos.salvar(veiculo)

    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharVeiculo(veiculos).executar(veiculo.id)


async def test_veiculo_inexistente_nao_e_encontrado(veiculos):
    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharVeiculo(veiculos).executar(uuid4())
