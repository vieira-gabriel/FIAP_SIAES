from application.ports.password_hasher import PasswordHasher
from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import UsuarioRepository
from domain.value_objects.perfil_usuario import PerfilUsuario


class CadastrarUsuario:
    """O Gerente cria o acesso de um funcionário e define o perfil (RF-03)."""

    def __init__(self, usuarios: UsuarioRepository, password_hasher: PasswordHasher):
        self._usuarios = usuarios
        self._password_hasher = password_hasher

    async def executar(self, nome: str, email: str, senha: str, perfil: PerfilUsuario) -> Usuario:
        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=await self._password_hasher.gerar_hash(senha),
            perfil=perfil,
        )
        await self._usuarios.garantir_email_livre(usuario)
        await self._usuarios.salvar(usuario)
        return usuario
