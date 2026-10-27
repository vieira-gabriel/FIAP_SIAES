import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from infrastructure.config import ConfiguracaoInvalida, carregar_configuracao
from infrastructure.database.engine import criar_engine

# O .env aponta para o host `db`, que só existe na rede do Compose; o teste roda fora dela.
HOST_DO_TESTE = "localhost"
ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture
async def banco_temporario(monkeypatch):
    """Banco vazio e descartável, para as migrations não tocarem o banco de desenvolvimento."""
    try:
        configuracao = carregar_configuracao()
    except ConfiguracaoInvalida:
        pytest.skip("Preencha o .env para rodar os testes de integração.")
    nome = f"teste_migrations_{uuid4().hex}"
    conexao_base = {
        "host": HOST_DO_TESTE,
        "porta": configuracao.postgres_port,
        "usuario": configuracao.postgres_user,
        "senha": configuracao.postgres_password.get_secret_value(),
    }
    administrador = criar_engine(banco=configuracao.postgres_db, **conexao_base).execution_options(
        isolation_level="AUTOCOMMIT"
    )
    try:
        async with administrador.connect() as conexao:
            await conexao.execute(text(f'CREATE DATABASE "{nome}"'))
    except OSError:
        await administrador.dispose()
        pytest.skip(
            "PostgreSQL indisponível em localhost: suba o db com "
            "`docker compose -f docker-compose.yml -f docker-compose.testes.yml up -d db`."
        )
    monkeypatch.setenv("POSTGRES_HOST", HOST_DO_TESTE)
    monkeypatch.setenv("POSTGRES_DB", nome)
    engine = criar_engine(banco=nome, **conexao_base)
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
