from uuid import UUID

from domain.entities.cliente import Cliente
from domain.repositories.cliente_repository import ClienteRepository


class DetalharCliente:
    """Consulta de um cliente ativo pelo id (RF-04)."""

    def __init__(self, clientes: ClienteRepository):
        self._clientes = clientes

    async def executar(self, id: UUID) -> Cliente:
        return await self._clientes.buscar_ativo_por_id(id)
