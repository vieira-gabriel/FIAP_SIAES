"""Impasse real entre duas transações no PostgreSQL e a repetição do caso de uso (RF-19, RF-23)."""

import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from infrastructure.database.repeticao_em_impasse import com_repeticao_em_impasse
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy


@pytest.fixture
async def tabela_de_impasse(engine: AsyncEngine) -> AsyncIterator[None]:
    async with engine.begin() as conexao:
        await conexao.execute(text("CREATE TABLE impasse_teste (id INT PRIMARY KEY, valor INT)"))
        await conexao.execute(text("INSERT INTO impasse_teste VALUES (1, 0), (2, 0)"))
    yield
    async with engine.begin() as conexao:
        await conexao.execute(text("DROP TABLE impasse_teste"))


class AtualizaEmOrdem:
    """Atualiza duas linhas na ordem dada. Na primeira tentativa, espera o outro caso de uso
    travar a primeira linha, para as duas transações se cruzarem."""

    def __init__(self, sessao: AsyncSession, ordem: tuple[int, int], cruzamento: asyncio.Barrier):
        self._sessao = sessao
        self._ordem = ordem
        self._cruzamento = cruzamento
        self.tentativas = 0

    async def executar(self) -> int:
        self.tentativas += 1
        primeira, segunda = self._ordem
        await self._atualizar(primeira)
        if self.tentativas == 1:
            await self._cruzamento.wait()
        await self._atualizar(segunda)
        return self.tentativas

    async def _atualizar(self, id: int) -> None:
        await self._sessao.execute(
            text("UPDATE impasse_teste SET valor = valor + 1 WHERE id = :id"), {"id": id}
        )


async def _executar(fabrica, ordem, cruzamento) -> int:
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica) as unidade:
        caso = AtualizaEmOrdem(unidade.sessao, ordem, cruzamento)
        return await com_repeticao_em_impasse(caso, unidade.sessao).executar()


async def test_impasse_real_aborta_uma_transacao_e_a_repeticao_conclui_as_duas(
    engine, tabela_de_impasse
):
    fabrica = async_sessionmaker(bind=engine, expire_on_commit=False)
    cruzamento = asyncio.Barrier(2)

    tentativas = await asyncio.gather(
        _executar(fabrica, (1, 2), cruzamento), _executar(fabrica, (2, 1), cruzamento)
    )

    assert sorted(tentativas) == [1, 2]
    async with engine.connect() as conexao:
        valores = (await conexao.execute(text("SELECT valor FROM impasse_teste"))).scalars().all()
    assert valores == [2, 2]
