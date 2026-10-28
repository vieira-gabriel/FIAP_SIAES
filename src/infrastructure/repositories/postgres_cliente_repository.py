from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.cliente import Cliente
from domain.repositories.cliente_repository import ClienteRepository
from domain.value_objects.documento import Documento
from infrastructure.database.cliente_model import ClienteModel


class PostgresClienteRepository(ClienteRepository):
    """Usa a sessão da unidade de trabalho; quem confirma a transação é ela (RNF-08)."""

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, cliente: Cliente) -> None:
        await self._sessao.merge(_para_modelo(cliente))

    async def buscar_por_id(self, id: UUID) -> Cliente | None:
        modelo = await self._sessao.get(ClienteModel, id)
        return _para_entidade(modelo) if modelo else None

    async def buscar_por_documento(self, documento: Documento) -> Cliente | None:
        consulta = select(ClienteModel).where(ClienteModel.documento == documento.valor)
        modelo = await self._sessao.scalar(consulta)
        return _para_entidade(modelo) if modelo else None

    async def listar(self) -> list[Cliente]:
        consulta = (
            select(ClienteModel)
            .where(ClienteModel.ativo.is_(True))
            .order_by(ClienteModel.nome, ClienteModel.id)
        )
        modelos = await self._sessao.scalars(consulta)
        return [_para_entidade(modelo) for modelo in modelos]


def _para_modelo(cliente: Cliente) -> ClienteModel:
    return ClienteModel(
        id=cliente.id,
        nome=cliente.nome,
        documento=cliente.documento.valor,
        email=cliente.email,
        telefone=cliente.telefone,
        ativo=cliente.ativo,
    )


def _para_entidade(modelo: ClienteModel) -> Cliente:
    return Cliente(
        id=modelo.id,
        nome=modelo.nome,
        documento=Documento.de_texto(modelo.documento),
        email=modelo.email,
        telefone=modelo.telefone,
        ativo=modelo.ativo,
    )
