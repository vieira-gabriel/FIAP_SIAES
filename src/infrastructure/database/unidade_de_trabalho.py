from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.ports.unidade_de_trabalho import UnidadeDeTrabalho


class UnidadeDeTrabalhoSqlAlchemy(UnidadeDeTrabalho):
    """Uma sessão do SQLAlchemy por bloco `async with`, fechada ao sair mesmo com erro."""

    def __init__(self, fabrica_de_sessoes: async_sessionmaker[AsyncSession]):
        self._fabrica_de_sessoes = fabrica_de_sessoes
        self._sessao: AsyncSession | None = None

    @property
    def sessao(self) -> AsyncSession:
        if self._sessao is None:
            raise RuntimeError("A sessão só existe dentro do bloco `async with`.")
        return self._sessao

    async def __aenter__(self) -> Self:
        self._sessao = self._fabrica_de_sessoes()
        return self

    async def __aexit__(
        self,
        tipo_excecao: type[BaseException] | None,
        excecao: BaseException | None,
        rastreamento: TracebackType | None,
    ) -> None:
        try:
            await super().__aexit__(tipo_excecao, excecao, rastreamento)
        finally:
            await self.sessao.close()
            self._sessao = None

    async def confirmar(self) -> None:
        await self.sessao.commit()

    async def desfazer(self) -> None:
        await self.sessao.rollback()
