from domain.entities.cliente import Cliente
from domain.repositories.cliente_repository import ClienteRepository


class ListarClientes:
    """Clientes ativos, em ordem de nome; os excluídos ficam fora (RF-04, RF-06)."""

    def __init__(self, clientes: ClienteRepository):
        self._clientes = clientes

    async def executar(self) -> list[Cliente]:
        return await self._clientes.listar()
