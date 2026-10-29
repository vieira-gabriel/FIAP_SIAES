"""Fixtures dos testes de integração contra o PostgreSQL do Compose (RNF-13).

Suba o banco antes: `docker compose -f docker-compose.yml -f docker-compose.testes.yml up -d db`.
Sem o `.env` preenchido ou sem o banco no ar, os testes de integração são pulados; no CI
(`CI=true`), eles falham.

A sessão de testes recria o banco `<POSTGRES_DB>_test`, aplica as migrations nele e o apaga no
final; o banco de desenvolvimento não é tocado. Cada teste roda dentro de uma transação desfeita
ao final, para um teste não enxergar o que outro gravou.

Os testes que precisam de um banco só deles, como os de migrations e de login pela aplicação
inteira, usam `banco_temporario` ou `banco_migrado`.
"""

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import NoReturn
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker

from infrastructure.config import Configuracao, ConfiguracaoInvalida, carregar_configuracao
from infrastructure.database.engine import criar_engine
from presentation.main import app

# O .env aponta para o host `db`, que só existe na rede do Compose; os testes rodam fora dela.
# É o endereço publicado pelo docker-compose.testes.yml. `localhost` tentaria antes o IPv6 e,
# no Windows, levaria cerca de 2 s para cair no IPv4, estourando o tempo limite do /health.
HOST_DO_TESTE = "127.0.0.1"
ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture(scope="session")
def configuracao() -> Configuracao:
    try:
        return carregar_configuracao()
    except ConfiguracaoInvalida:
        _pular_fora_do_ci("Preencha o .env para rodar os testes de integração.")


@pytest.fixture(scope="session")
def parametros_de_conexao(configuracao: Configuracao) -> dict:
    return {
        "host": HOST_DO_TESTE,
        "porta": configuracao.postgres_port,
        "usuario": configuracao.postgres_user,
        "senha": configuracao.postgres_password.get_secret_value(),
    }


@pytest.fixture(scope="session")
def banco_de_teste(configuracao: Configuracao, parametros_de_conexao: dict) -> Iterator[str]:
    """Síncrona, com `asyncio.run`, porque as fixtures de sessão não compartilham o loop dos
    testes, e o Alembic abre o próprio loop."""
    nome = f"{configuracao.postgres_db}_test"
    administrador = {"banco": configuracao.postgres_db, **parametros_de_conexao}
    try:
        asyncio.run(
            _executar_como_administrador(
                administrador,
                f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)',
                f'CREATE DATABASE "{nome}"',
            )
        )
    except OSError:
        _pular_fora_do_ci(
            "PostgreSQL indisponível em 127.0.0.1: suba o db com "
            "`docker compose -f docker-compose.yml -f docker-compose.testes.yml up -d db`."
        )
    with pytest.MonkeyPatch.context() as ambiente:
        # As migrations e a aplicação leem a conexão do ambiente; durante a sessão ele aponta
        # para o banco de teste.
        ambiente.setenv("POSTGRES_HOST", HOST_DO_TESTE)
        ambiente.setenv("POSTGRES_DB", nome)
        command.upgrade(Config(str(ALEMBIC_INI)), "head")
        yield nome
    asyncio.run(
        _executar_como_administrador(
            administrador, f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'
        )
    )


@pytest.fixture
async def engine(banco_de_teste: str, parametros_de_conexao: dict) -> AsyncIterator[AsyncEngine]:
    engine = criar_engine(banco=banco_de_teste, **parametros_de_conexao)
    yield engine
    await engine.dispose()


@pytest.fixture
async def conexao(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """Transação externa desfeita ao final do teste: nada do que o teste grava permanece."""
    async with engine.connect() as conexao:
        transacao = await conexao.begin()
        yield conexao
        await transacao.rollback()


@pytest.fixture
def fabrica_de_sessoes(conexao: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    """Sessões presas à transação do teste. O `commit` de uma unidade de trabalho só fecha um
    savepoint, e a transação externa ainda desfaz tudo no final."""
    return async_sessionmaker(
        bind=conexao, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
async def cliente_http(
    fabrica_de_sessoes: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """Cliente da aplicação real, com o ciclo de vida executado no mesmo loop do teste.

    A fábrica de sessões do container é trocada pela do teste, para as rotas gravarem dentro da
    transação que é desfeita no final.
    """
    async with app.router.lifespan_context(app):
        app.state.fabrica_de_sessoes = fabrica_de_sessoes
        transporte = ASGITransport(app=app)
        async with AsyncClient(transport=transporte, base_url="http://teste") as cliente:
            yield cliente


@pytest.fixture
def config_do_alembic() -> Config:
    return Config(str(ALEMBIC_INI))


@pytest.fixture
def aplicar_migrations(config_do_alembic: Config):
    async def aplicar() -> None:
        await asyncio.to_thread(command.upgrade, config_do_alembic, "head")

    return aplicar


@pytest.fixture
async def banco_temporario(
    monkeypatch, banco_de_teste: str, parametros_de_conexao: dict
) -> AsyncIterator[AsyncEngine]:
    """Banco vazio e só deste teste, para ele não tocar o `banco_de_teste` compartilhado.

    Aponta `POSTGRES_DB` para ele, então o Alembic e a aplicação o usam.
    """
    nome = f"teste_{uuid4().hex}"
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


@pytest.fixture
async def banco_migrado(banco_temporario: AsyncEngine, aplicar_migrations) -> AsyncEngine:
    await aplicar_migrations()
    return banco_temporario


def _pular_fora_do_ci(motivo: str) -> NoReturn:
    """No CI (o GitHub Actions define `CI=true`), falha em vez de pular: um teste de integração
    pulado ali esconderia um banco que não subiu."""
    if os.environ.get("CI") == "true":
        pytest.fail(motivo)
    pytest.skip(motivo)


async def _executar_como_administrador(parametros: dict, *comandos_sql: str) -> None:
    """`CREATE DATABASE` e `DROP DATABASE` não rodam dentro de transação, daí o `AUTOCOMMIT`."""
    engine = criar_engine(**parametros).execution_options(isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conexao:
            for comando_sql in comandos_sql:
                await conexao.execute(text(comando_sql))
    finally:
        await engine.dispose()
