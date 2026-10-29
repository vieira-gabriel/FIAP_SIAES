from uuid import UUID

from domain.entities.veiculo import Veiculo
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.placa import Placa


class AtualizarVeiculo:
    """Atualização dos dados de um veículo ativo, sem troca do proprietário (RF-07, RF-08)."""

    def __init__(self, veiculos: VeiculoRepository):
        self._veiculos = veiculos

    async def executar(self, id: UUID, placa: Placa, marca: str, modelo: str, ano: int) -> Veiculo:
        veiculo = await self._veiculos.buscar_ativo_por_id(id)
        veiculo.atualizar_dados(placa, marca, modelo, ano)
        await self._veiculos.garantir_placa_livre(veiculo)
        await self._veiculos.salvar(veiculo)
        return veiculo
