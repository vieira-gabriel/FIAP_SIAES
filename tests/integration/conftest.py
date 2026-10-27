import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from infrastructure.config import ConfiguracaoInvalida, carregar_configuracao
from infrastructure.database.engine import criar_engine

# O .env aponta para o host `db`, que só existe na rede do Compose; o teste roda fora dela.
HOST_DO_TESTE = "localhost"
ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture
def config_do_alembic() -> Config:
    return Config(str(ALEMBIC_INI))


@pytest.fixture
def aplicar_migrations(config_do_alembic):
    async def aplicar() -> None:
        await asyncio.to_thread(command.upgrade, config_do_alembic, "head")

    return aplicar


@pytest.fixture
async def banco_temporario(monkeypatch):
    """Banco vazio e descartável, para os testes não tocarem o banco de desenvolvimento.

    Aponta `POSTGRES_HOST` e `POSTGRES_DB` para ele, então o Alembic e a aplicação o usam.
    """
    try:
        configuracao = carregar_configuracao()
    except ConfiguracaoInvalida:
        pytest.skip("Preencha o .env para rodar os testes de integração.")
    nome = f"teste_{uuid4().hex}"
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


@pytest.fixture
async def banco_migrado(banco_temporario, aplicar_migrations):
    await aplicar_migrations()
    return banco_temporario
