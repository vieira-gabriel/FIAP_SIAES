from uuid import uuid4

import pytest

from domain.entities.veiculo import Veiculo
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.placa import Placa


class VeiculoRepositoryEmMemoria(VeiculoRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, veiculo):
        self.dados[veiculo.id] = veiculo

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_placa(self, placa):
        return next((v for v in self.dados.values() if v.placa == placa), None)


def test_porta_define_salvar_e_buscas_por_id_e_placa():
    assert VeiculoRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_placa",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemBuscaPorPlaca(VeiculoRepository):
        async def salvar(self, veiculo): ...

        async def buscar_por_id(self, id): ...

    with pytest.raises(TypeError):
        SemBuscaPorPlaca()


async def test_busca_por_placa_independe_do_formato_digitado():
    repositorio = VeiculoRepositoryEmMemoria()
    veiculo = Veiculo(
        cliente_id=uuid4(), placa=Placa("abc-1d23"), marca="Fiat", modelo="Uno", ano=2015
    )
    await repositorio.salvar(veiculo)

    assert await repositorio.buscar_por_placa(Placa("ABC1D23")) == veiculo
    assert await repositorio.buscar_por_id(veiculo.id) == veiculo
    assert await repositorio.buscar_por_placa(Placa("XYZ9876")) is None
