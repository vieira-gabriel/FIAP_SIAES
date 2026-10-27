from dataclasses import dataclass, field

from application.ports.password_hasher import PasswordHasher
from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import UsuarioRepository
from domain.value_objects.perfil_usuario import PerfilUsuario


@dataclass(frozen=True)
class SenhasDaCargaInicial:
    """Senhas lidas do ambiente (RF-03, RNF-06). Sem a senha de um usuário de demonstração,
    ele não é criado; o container só as informa quando `SEED_DEMO=true`."""

    gerente: str = field(repr=False)
    atendente: str | None = field(default=None, repr=False)
    mecanico: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class _UsuarioDaCargaInicial:
    nome: str
    email: str
    perfil: PerfilUsuario


_GERENTE_PADRAO = _UsuarioDaCargaInicial(
    "Administrador", "admin@oficina.com", PerfilUsuario.GERENTE
)
_ATENDENTE_DE_DEMONSTRACAO = _UsuarioDaCargaInicial(
    "Atendente de Demonstração", "atendente@oficina.com", PerfilUsuario.ATENDENTE
)
_MECANICO_DE_DEMONSTRACAO = _UsuarioDaCargaInicial(
    "Mecânico de Demonstração", "mecanico@oficina.com", PerfilUsuario.MECANICO
)


class CriarCargaInicial:
    """Cria o Gerente padrão e, opcionalmente, os usuários de demonstração na subida (RF-03).

    Usuário com o e-mail já cadastrado é mantido como está, sem duplicar nem redefinir a senha,
    para que a reinicialização do container não desfaça alterações feitas depois.
    """

    def __init__(self, usuarios: UsuarioRepository, password_hasher: PasswordHasher):
        self._usuarios = usuarios
        self._password_hasher = password_hasher

    async def executar(self, senhas: SenhasDaCargaInicial) -> None:
        await self._criar_se_ausente(_GERENTE_PADRAO, senhas.gerente)
        if senhas.atendente is not None:
            await self._criar_se_ausente(_ATENDENTE_DE_DEMONSTRACAO, senhas.atendente)
        if senhas.mecanico is not None:
            await self._criar_se_ausente(_MECANICO_DE_DEMONSTRACAO, senhas.mecanico)

    async def _criar_se_ausente(self, dados: _UsuarioDaCargaInicial, senha: str) -> None:
        if await self._usuarios.buscar_por_email(dados.email) is not None:
            return
        await self._usuarios.salvar(
            Usuario(
                nome=dados.nome,
                email=dados.email,
                senha_hash=await self._password_hasher.gerar_hash(senha),
                perfil=dados.perfil,
            )
        )
