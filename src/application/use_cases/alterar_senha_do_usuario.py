from uuid import UUID

from application.ports.password_hasher import PasswordHasher
from domain.repositories.usuario_repository import UsuarioRepository


class AlterarSenhaDoUsuario:
    """O Gerente define uma nova senha; só o hash é gravado (RF-03, RNF-06)."""

    def __init__(self, usuarios: UsuarioRepository, password_hasher: PasswordHasher):
        self._usuarios = usuarios
        self._password_hasher = password_hasher

    async def executar(self, id: UUID, senha: str) -> None:
        usuario = await self._usuarios.buscar_existente_por_id(id)
        usuario.alterar_senha_hash(await self._password_hasher.gerar_hash(senha))
        await self._usuarios.salvar(usuario)
