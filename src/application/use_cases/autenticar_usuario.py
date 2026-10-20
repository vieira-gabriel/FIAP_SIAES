from application.ports.password_hasher import PasswordHasher
from application.ports.token_service import TokenService
from domain.exceptions import CredenciaisInvalidas
from domain.repositories.usuario_repository import UsuarioRepository


class AutenticarUsuario:
    """Login de usuário interno com e-mail e senha, devolvendo o token JWT (RF-01)."""

    def __init__(
        self,
        usuarios: UsuarioRepository,
        password_hasher: PasswordHasher,
        tokens: TokenService,
    ):
        self._usuarios = usuarios
        self._password_hasher = password_hasher
        self._tokens = tokens

    async def executar(self, email: str, senha: str) -> str:
        usuario = await self._usuarios.buscar_por_email(email.strip().lower())
        if usuario is None or not usuario.pode_autenticar():
            raise CredenciaisInvalidas()
        if not await self._password_hasher.verificar(senha, usuario.senha_hash):
            raise CredenciaisInvalidas()
        return self._tokens.emitir(usuario)
