from uuid import UUID

from domain.entities.veiculo import Veiculo
from domain.repositories.veiculo_repository import VeiculoRepository


class DetalharVeiculo:
    """Consulta de um veículo ativo pelo id (RF-07)."""

    def __init__(self, veiculos: VeiculoRepository):
        self._veiculos = veiculos

    async def executar(self, id: UUID) -> Veiculo:
        return await self._veiculos.buscar_ativo_por_id(id)
