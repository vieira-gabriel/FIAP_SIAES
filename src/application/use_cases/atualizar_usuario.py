from uuid import UUID

from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import UsuarioRepository
from domain.value_objects.perfil_usuario import PerfilUsuario


class AtualizarUsuario:
    """Atualização do nome, do e-mail e do perfil pelo Gerente (RF-03)."""

    def __init__(self, usuarios: UsuarioRepository):
        self._usuarios = usuarios

    async def executar(
        self, id: UUID, nome: str, email: str, perfil: PerfilUsuario, responsavel_id: UUID
    ) -> Usuario:
        usuario = await self._usuarios.buscar_existente_por_id(id)
        usuario.atualizar_dados(nome, email)
        usuario.alterar_perfil(perfil, responsavel_id)
        await self._usuarios.garantir_email_livre(usuario)
        await self._usuarios.salvar(usuario)
        return usuario
