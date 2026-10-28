from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import UsuarioRepository
from infrastructure.database.usuario_model import UsuarioModel


class PostgresUsuarioRepository(UsuarioRepository):
    """Usa a sessão da unidade de trabalho; quem confirma a transação é ela (RNF-08)."""

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, usuario: Usuario) -> None:
        await self._sessao.merge(_para_modelo(usuario))

    async def buscar_por_id(self, id: UUID) -> Usuario | None:
        modelo = await self._sessao.get(UsuarioModel, id)
        return _para_entidade(modelo) if modelo else None

    async def buscar_por_email(self, email: str) -> Usuario | None:
        consulta = select(UsuarioModel).where(UsuarioModel.email == email)
        modelo = await self._sessao.scalar(consulta)
        return _para_entidade(modelo) if modelo else None


def _para_modelo(usuario: Usuario) -> UsuarioModel:
    return UsuarioModel(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=usuario.senha_hash,
        perfil=usuario.perfil,
        ativo=usuario.ativo,
    )


def _para_entidade(modelo: UsuarioModel) -> Usuario:
    return Usuario(
        id=modelo.id,
        nome=modelo.nome,
        email=modelo.email,
        senha_hash=modelo.senha_hash,
        perfil=modelo.perfil,
        ativo=modelo.ativo,
    )
