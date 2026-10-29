from uuid import uuid4

import pytest

from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada, PlacaJaCadastrada
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.placa import Placa


def _veiculo(placa="ABC1D23", cliente_id=None):
    return Veiculo(
        cliente_id=cliente_id or uuid4(), placa=Placa(placa), marca="Fiat", modelo="Uno", ano=2015
    )


def test_porta_define_salvar_buscas_e_listagem():
    assert VeiculoRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_placa",
        "listar",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemBuscaPorPlaca(VeiculoRepository):
        async def salvar(self, veiculo): ...

        async def buscar_por_id(self, id): ...

        async def listar(self, cliente_id=None): ...

    with pytest.raises(TypeError):
        SemBuscaPorPlaca()


async def test_busca_por_placa_independe_do_formato_digitado(veiculos):
    veiculo = _veiculo(placa="abc-1d23")
    await veiculos.salvar(veiculo)

    assert await veiculos.buscar_por_placa(Placa("ABC1D23")) == veiculo
    assert await veiculos.buscar_por_id(veiculo.id) == veiculo
    assert await veiculos.buscar_por_placa(Placa("XYZ9876")) is None


async def test_busca_por_placa_ignora_o_veiculo_excluido(veiculos):
    excluido = _veiculo()
    excluido.excluir()
    await veiculos.salvar(excluido)

    assert await veiculos.buscar_por_placa(Placa("ABC1D23")) is None


async def test_buscar_ativo_por_id_devolve_o_veiculo_ativo(veiculos):
    veiculo = _veiculo()
    await veiculos.salvar(veiculo)

    assert await veiculos.buscar_ativo_por_id(veiculo.id) == veiculo


async def test_buscar_ativo_por_id_trata_o_veiculo_excluido_como_inexistente(veiculos):
    veiculo = _veiculo()
    veiculo.excluir()
    await veiculos.salvar(veiculo)

    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await veiculos.buscar_ativo_por_id(veiculo.id)

    assert erro.value.entidade == "Veículo"


async def test_buscar_ativo_por_id_inexistente(veiculos):
    with pytest.raises(EntidadeNaoEncontrada):
        await veiculos.buscar_ativo_por_id(uuid4())


async def test_placa_de_outro_veiculo_ativo_nao_esta_livre(veiculos):
    await veiculos.salvar(_veiculo())

    with pytest.raises(PlacaJaCadastrada):
        await veiculos.garantir_placa_livre(_veiculo())


async def test_placa_de_veiculo_excluido_esta_livre(veiculos):
    excluido = _veiculo()
    excluido.excluir()
    await veiculos.salvar(excluido)

    await veiculos.garantir_placa_livre(_veiculo())


async def test_a_propria_placa_continua_livre_para_o_dono(veiculos):
    veiculo = _veiculo()
    await veiculos.salvar(veiculo)

    await veiculos.garantir_placa_livre(veiculo)
