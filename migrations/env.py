import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

# Um modelo só entra no `Base.metadata`, e portanto no autogenerate, depois de importado.
import infrastructure.database.cliente_model  # noqa: F401
import infrastructure.database.usuario_model  # noqa: F401
import infrastructure.database.veiculo_model  # noqa: F401
from infrastructure.config import carregar_configuracao
from infrastructure.database.base import Base
from infrastructure.database.engine import criar_engine

config = context.config

# Sem desativar os loggers existentes, rodar as migrations dentro de um teste silenciaria os demais.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def executar_migrations(conexao: Connection) -> None:
    context.configure(connection=conexao, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def executar_migrations_assincronas() -> None:
    configuracao = carregar_configuracao()
    engine = criar_engine(
        host=configuracao.postgres_host,
        porta=configuracao.postgres_port,
        banco=configuracao.postgres_db,
        usuario=configuracao.postgres_user,
        senha=configuracao.postgres_password.get_secret_value(),
    )
    try:
        async with engine.connect() as conexao:
            await conexao.run_sync(executar_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("O modo offline (--sql) não é suportado; use `alembic upgrade head`.")

asyncio.run(executar_migrations_assincronas())
