from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.cliente import Cliente
from domain.value_objects.documento import Documento


class ClienteRepository(ABC):
    @abstractmethod
    async def salvar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Cliente | None: ...

    @abstractmethod
    async def buscar_por_documento(self, documento: Documento) -> Cliente | None: ...
