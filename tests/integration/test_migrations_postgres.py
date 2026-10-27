from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

import infrastructure.database.usuario_model  # noqa: F401
from infrastructure.database.base import Base


async def _versoes_aplicadas(engine) -> list[str]:
    async with engine.connect() as conexao:
        resultado = await conexao.execute(text("SELECT version_num FROM alembic_version"))
        return list(resultado.scalars())


def _cabeca(config_do_alembic) -> str:
    return ScriptDirectory.from_config(config_do_alembic).get_current_head()


async def test_banco_vazio_recebe_a_revisao_mais_recente(
    banco_temporario, aplicar_migrations, config_do_alembic
):
    await aplicar_migrations()

    assert await _versoes_aplicadas(banco_temporario) == [_cabeca(config_do_alembic)]


async def test_aplicar_de_novo_nao_falha_nem_reaplica(
    banco_temporario, aplicar_migrations, config_do_alembic
):
    await aplicar_migrations()
    await aplicar_migrations()

    assert await _versoes_aplicadas(banco_temporario) == [_cabeca(config_do_alembic)]


async def test_migrations_correspondem_aos_modelos_do_orm(banco_migrado):
    """Sem isso, um modelo alterado sem migration só falharia em produção."""
    async with banco_migrado.connect() as conexao:
        diferencas = await conexao.run_sync(
            lambda sincrona: compare_metadata(MigrationContext.configure(sincrona), Base.metadata)
        )

    assert diferencas == []
