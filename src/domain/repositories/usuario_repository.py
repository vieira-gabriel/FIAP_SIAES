from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.usuario import Usuario
from domain.exceptions import EmailJaCadastrado, EntidadeNaoEncontrada


class UsuarioRepository(ABC):
    @abstractmethod
    async def salvar(self, usuario: Usuario) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Usuario | None: ...

    @abstractmethod
    async def buscar_por_email(self, email: str) -> Usuario | None: ...

    @abstractmethod
    async def listar(self) -> list[Usuario]:
        """Ativos e desativados, em ordem de nome: o Gerente precisa ver quem pode reativar."""

    async def buscar_existente_por_id(self, id: UUID) -> Usuario:
        """O usuário desativado continua acessível, para ser consultado e reativado (RF-03)."""
        usuario = await self.buscar_por_id(id)
        if usuario is None:
            raise EntidadeNaoEncontrada("Usuário", id)
        return usuario

    async def garantir_email_livre(self, usuario: Usuario) -> None:
        dono_do_email = await self.buscar_por_email(usuario.email)
        if dono_do_email is not None and dono_do_email != usuario:
            raise EmailJaCadastrado()
