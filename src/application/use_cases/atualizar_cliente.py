from uuid import UUID

from domain.entities.cliente import Cliente
from domain.repositories.cliente_repository import ClienteRepository
from domain.value_objects.documento import Documento


class AtualizarCliente:
    """Atualização dos dados de um cliente ativo (RF-04, RF-05)."""

    def __init__(self, clientes: ClienteRepository):
        self._clientes = clientes

    async def executar(
        self, id: UUID, nome: str, documento: Documento, email: str, telefone: str
    ) -> Cliente:
        cliente = await self._clientes.buscar_ativo_por_id(id)
        cliente.atualizar_dados(nome, documento, email, telefone)
        await self._clientes.garantir_documento_livre(cliente)
        await self._clientes.salvar(cliente)
        return cliente
