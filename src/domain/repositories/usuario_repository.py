from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.usuario import Usuario


class UsuarioRepository(ABC):
    @abstractmethod
    async def salvar(self, usuario: Usuario) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Usuario | None: ...

    @abstractmethod
    async def buscar_por_email(self, email: str) -> Usuario | None: ...
