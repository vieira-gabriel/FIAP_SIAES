from uuid import UUID

from domain.entities.veiculo import Veiculo
from domain.repositories.veiculo_repository import VeiculoRepository


class ListarVeiculos:
    """Veículos ativos, em ordem de placa, opcionalmente só os de um cliente (RF-07, RF-09)."""

    def __init__(self, veiculos: VeiculoRepository):
        self._veiculos = veiculos

    async def executar(self, cliente_id: UUID | None = None) -> list[Veiculo]:
        return await self._veiculos.listar(cliente_id)
