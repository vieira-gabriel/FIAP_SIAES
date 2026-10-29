from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.cliente import Cliente
from domain.exceptions import DocumentoJaCadastrado, EntidadeNaoEncontrada
from domain.value_objects.documento import Documento


class ClienteRepository(ABC):
    @abstractmethod
    async def salvar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Cliente | None: ...

    @abstractmethod
    async def buscar_por_documento(self, documento: Documento) -> Cliente | None:
        """Também encontra o cliente excluído, porque o documento continua reservado a ele."""

    @abstractmethod
    async def listar(self) -> list[Cliente]:
        """Só os clientes ativos, em ordem de nome (RF-04, RF-06)."""

    async def buscar_ativo_por_id(self, id: UUID) -> Cliente:
        """Para o cadastro, o cliente excluído deixa de existir; as OS dele continuam (RF-06)."""
        cliente = await self.buscar_por_id(id)
        if cliente is None or not cliente.ativo:
            raise EntidadeNaoEncontrada("Cliente", id)
        return cliente

    async def garantir_documento_livre(self, cliente: Cliente) -> None:
        """O documento identifica um só cliente, inclusive um excluído (RF-04, RF-06)."""
        dono_do_documento = await self.buscar_por_documento(cliente.documento)
        if dono_do_documento is not None and dono_do_documento != cliente:
            raise DocumentoJaCadastrado()
