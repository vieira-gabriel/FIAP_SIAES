from uuid import UUID

from domain.repositories.usuario_repository import UsuarioRepository


class DesativarUsuario:
    """O usuário desativado não faz login, e o registro é mantido (RF-03)."""

    def __init__(self, usuarios: UsuarioRepository):
        self._usuarios = usuarios

    async def executar(self, id: UUID, responsavel_id: UUID) -> None:
        usuario = await self._usuarios.buscar_existente_por_id(id)
        usuario.desativar_por(responsavel_id)
        await self._usuarios.salvar(usuario)
