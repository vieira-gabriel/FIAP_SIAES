import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from infrastructure.database.engine import criar_engine

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture
async def banco_temporario(monkeypatch, banco_de_teste, parametros_de_conexao):
    """Banco vazio e próprio deste teste: o `banco_de_teste` já recebeu as migrations."""
    nome = f"teste_migrations_{uuid4().hex}"
    administrador = criar_engine(banco=banco_de_teste, **parametros_de_conexao).execution_options(
        isolation_level="AUTOCOMMIT"
    )
    async with administrador.connect() as conexao:
        await conexao.execute(text(f'CREATE DATABASE "{nome}"'))
    monkeypatch.setenv("POSTGRES_DB", nome)
    engine = criar_engine(banco=nome, **parametros_de_conexao)
    yield engine
    await engine.dispose()
    async with administrador.connect() as conexao:
        await conexao.execute(text(f'DROP DATABASE "{nome}" WITH (FORCE)'))
    await administrador.dispose()


def _config() -> Config:
    return Config(str(ALEMBIC_INI))


async def _aplicar_migrations() -> None:
    await asyncio.to_thread(command.upgrade, _config(), "head")


async def _versoes_aplicadas(engine) -> list[str]:
    async with engine.connect() as conexao:
        resultado = await conexao.execute(text("SELECT version_num FROM alembic_version"))
        return list(resultado.scalars())


async def test_banco_vazio_recebe_a_revisao_mais_recente(banco_temporario):
    await _aplicar_migrations()

    cabeca = ScriptDirectory.from_config(_config()).get_current_head()
    assert await _versoes_aplicadas(banco_temporario) == [cabeca]


async def test_aplicar_de_novo_nao_falha_nem_reaplica(banco_temporario):
    await _aplicar_migrations()
    await _aplicar_migrations()

    cabeca = ScriptDirectory.from_config(_config()).get_current_head()
    assert await _versoes_aplicadas(banco_temporario) == [cabeca]
