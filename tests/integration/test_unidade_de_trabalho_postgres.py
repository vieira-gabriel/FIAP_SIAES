from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from infrastructure.database.engine import criar_fabrica_de_sessoes
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy


@pytest.fixture
async def tabela(engine):
    nome = f"teste_unidade_de_trabalho_{uuid4().hex}"
    async with engine.begin() as conexao:
        await conexao.execute(text(f"CREATE TABLE {nome} (id integer PRIMARY KEY)"))
    yield nome
    async with engine.begin() as conexao:
        await conexao.execute(text(f"DROP TABLE {nome}"))


@pytest.fixture
def unidade(engine):
    return UnidadeDeTrabalhoSqlAlchemy(criar_fabrica_de_sessoes(engine))


async def _inserir(unidade, tabela, id):
    await unidade.sessao.execute(text(f"INSERT INTO {tabela} (id) VALUES (:id)"), {"id": id})


async def _contar(engine, tabela):
    async with engine.connect() as conexao:
        resultado = await conexao.execute(text(f"SELECT count(*) FROM {tabela}"))
        return resultado.scalar_one()


async def test_bloco_sem_excecao_confirma_todas_as_escritas(engine, tabela, unidade):
    async with unidade:
        await _inserir(unidade, tabela, 1)
        await _inserir(unidade, tabela, 2)

    assert await _contar(engine, tabela) == 2


async def test_excecao_no_meio_do_bloco_desfaz_todas_as_escritas(engine, tabela, unidade):
    with pytest.raises(RuntimeError):
        async with unidade:
            await _inserir(unidade, tabela, 1)
            await _inserir(unidade, tabela, 2)
            raise RuntimeError("falha no meio da operação")

    assert await _contar(engine, tabela) == 0


async def test_violacao_de_integridade_desfaz_as_escritas_anteriores(engine, tabela, unidade):
    with pytest.raises(IntegrityError):
        async with unidade:
            await _inserir(unidade, tabela, 1)
            await _inserir(unidade, tabela, 1)

    assert await _contar(engine, tabela) == 0


async def test_sessao_so_existe_dentro_do_bloco(tabela, unidade):
    async with unidade:
        await _inserir(unidade, tabela, 1)

    with pytest.raises(RuntimeError):
        _ = unidade.sessao
