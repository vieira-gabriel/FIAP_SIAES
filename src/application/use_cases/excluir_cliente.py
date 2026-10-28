from uuid import UUID

from domain.repositories.cliente_repository import ClienteRepository


class ExcluirCliente:
    """Exclusão lógica: o cliente sai do cadastro e as OS dele são preservadas (RF-06)."""

    def __init__(self, clientes: ClienteRepository):
        self._clientes = clientes

    async def executar(self, id: UUID) -> None:
        cliente = await self._clientes.buscar_ativo_por_id(id)
        cliente.excluir()
        await self._clientes.salvar(cliente)
