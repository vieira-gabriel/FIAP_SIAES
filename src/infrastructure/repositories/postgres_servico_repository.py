from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.servico import Servico
from domain.repositories.servico_repository import ServicoRepository
from domain.value_objects.valor import Valor
from infrastructure.database.servico_model import ServicoModel


class PostgresServicoRepository(ServicoRepository):
    """Usa a sessão da unidade de trabalho; quem confirma a transação é ela (RNF-08)."""

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, servico: Servico) -> None:
        await self._sessao.merge(_para_modelo(servico))

    async def buscar_por_id(self, id: UUID) -> Servico | None:
        modelo = await self._sessao.get(ServicoModel, id)
        return _para_entidade(modelo) if modelo else None

    async def buscar_por_codigo(self, codigo: str) -> Servico | None:
        consulta = select(ServicoModel).where(ServicoModel.codigo == codigo)
        modelo = await self._sessao.scalar(consulta)
        return _para_entidade(modelo) if modelo else None

    async def listar(self) -> list[Servico]:
        consulta = (
            select(ServicoModel)
            .where(ServicoModel.ativo.is_(True))
            .order_by(ServicoModel.nome, ServicoModel.id)
        )
        return [_para_entidade(modelo) for modelo in await self._sessao.scalars(consulta)]


def _para_modelo(servico: Servico) -> ServicoModel:
    return ServicoModel(
        id=servico.id,
        codigo=servico.codigo,
        nome=servico.nome,
        descricao=servico.descricao,
        valor_base=servico.valor_base.valor,
        tempo_estimado_minutos=servico.tempo_estimado_minutos,
        ativo=servico.ativo,
    )


def _para_entidade(modelo: ServicoModel) -> Servico:
    return Servico(
        id=modelo.id,
        codigo=modelo.codigo,
        nome=modelo.nome,
        descricao=modelo.descricao,
        valor_base=Valor(modelo.valor_base),
        tempo_estimado_minutos=modelo.tempo_estimado_minutos,
        ativo=modelo.ativo,
    )
