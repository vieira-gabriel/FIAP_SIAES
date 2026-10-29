from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import UsuarioRepository


class ListarUsuarios:
    """Todos os usuários, ativos e desativados, em ordem de nome (RF-03)."""

    def __init__(self, usuarios: UsuarioRepository):
        self._usuarios = usuarios

    async def executar(self) -> list[Usuario]:
        return await self._usuarios.listar()
