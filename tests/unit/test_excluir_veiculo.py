from uuid import uuid4

import pytest

from application.use_cases.excluir_veiculo import ExcluirVeiculo
from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.placa import Placa


def _veiculo():
    return Veiculo(cliente_id=uuid4(), placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2015)


async def test_exclusao_logica_mantem_o_registro_inativo(veiculos):
    veiculo = _veiculo()
    await veiculos.salvar(veiculo)

    await ExcluirVeiculo(veiculos).executar(veiculo.id)

    salvo = await veiculos.buscar_por_id(veiculo.id)
    assert salvo is not None
    assert not salvo.ativo


async def test_excluir_de_novo_nao_encontra_o_veiculo(veiculos):
    veiculo = _veiculo()
    await veiculos.salvar(veiculo)
    await ExcluirVeiculo(veiculos).executar(veiculo.id)

    with pytest.raises(EntidadeNaoEncontrada):
        await ExcluirVeiculo(veiculos).executar(veiculo.id)
