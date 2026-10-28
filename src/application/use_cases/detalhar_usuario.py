from uuid import UUID

from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import UsuarioRepository


class DetalharUsuario:
    def __init__(self, usuarios: UsuarioRepository):
        self._usuarios = usuarios

    async def executar(self, id: UUID) -> Usuario:
        return await self._usuarios.buscar_existente_por_id(id)
