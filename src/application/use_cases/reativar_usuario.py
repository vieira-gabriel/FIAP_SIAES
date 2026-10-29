from uuid import UUID

from domain.repositories.usuario_repository import UsuarioRepository


class ReativarUsuario:
    def __init__(self, usuarios: UsuarioRepository):
        self._usuarios = usuarios

    async def executar(self, id: UUID) -> None:
        usuario = await self._usuarios.buscar_existente_por_id(id)
        usuario.reativar()
        await self._usuarios.salvar(usuario)
