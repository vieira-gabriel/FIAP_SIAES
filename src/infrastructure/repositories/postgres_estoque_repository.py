from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.estoque_peca import EstoquePeca
from domain.repositories.estoque_repository import EstoqueRepository
from infrastructure.database.estoque_peca_model import EstoquePecaModel


class PostgresEstoqueRepository(EstoqueRepository):
    """Usa a sessão da unidade de trabalho; quem confirma a transação é ela (RNF-08)."""

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, estoque: EstoquePeca) -> None:
        await self._sessao.merge(_para_modelo(estoque))

    async def buscar_por_peca(self, peca_id: UUID) -> EstoquePeca | None:
        # `populate_existing` relê a linha depois do bloqueio, mesmo que a sessão já a tenha
        # carregado antes: o saldo usado é o gravado pela transação que liberou o bloqueio.
        consulta = (
            select(EstoquePecaModel)
            .where(EstoquePecaModel.peca_id == peca_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        modelo = await self._sessao.scalar(consulta)
        return _para_entidade(modelo) if modelo else None

    async def buscar_por_pecas(self, peca_ids: Collection[UUID]) -> dict[UUID, EstoquePeca]:
        consulta = select(EstoquePecaModel).where(EstoquePecaModel.peca_id.in_(peca_ids))
        return {
            modelo.peca_id: _para_entidade(modelo)
            for modelo in await self._sessao.scalars(consulta)
        }


def _para_modelo(estoque: EstoquePeca) -> EstoquePecaModel:
    return EstoquePecaModel(
        peca_id=estoque.peca_id,
        quantidade_fisica=estoque.quantidade_fisica,
        quantidade_reservada=estoque.quantidade_reservada,
    )


def _para_entidade(modelo: EstoquePecaModel) -> EstoquePeca:
    return EstoquePeca(
        peca_id=modelo.peca_id,
        quantidade_fisica=modelo.quantidade_fisica,
        quantidade_reservada=modelo.quantidade_reservada,
    )
