"""Exemplos de uso das fixtures de `conftest.py`, que servem de modelo para os próximos fluxos."""

import pytest
from sqlalchemy import text

from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy


async def test_aplicacao_responde_pela_rota_http_usando_o_banco_de_teste(cliente_http):
    resposta = await cliente_http.get("/health")

    assert resposta.status_code == 200
    assert resposta.json()["banco"] == "disponivel"


async def test_testes_rodam_no_banco_de_teste_com_as_migrations_aplicadas(conexao, banco_de_teste):
    banco_atual = await conexao.scalar(text("SELECT current_database()"))
    versao = await conexao.scalar(text("SELECT version_num FROM alembic_version"))

    assert banco_atual == banco_de_teste
    assert banco_atual.endswith("_test")
    assert versao is not None


@pytest.mark.parametrize("execucao", ["primeira", "segunda"])
async def test_um_teste_nao_enxerga_o_que_outro_gravou(conexao, fabrica_de_sessoes, execucao):
    """As duas execuções criam a mesma tabela e gravam a mesma chave; a segunda só passa se a
    primeira tiver sido desfeita."""
    await conexao.execute(text("CREATE TABLE exemplo_isolamento (id integer PRIMARY KEY)"))

    unidade = UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes)
    async with unidade:
        await unidade.sessao.execute(text("INSERT INTO exemplo_isolamento (id) VALUES (1)"))

    assert await conexao.scalar(text("SELECT count(*) FROM exemplo_isolamento")) == 1


async def test_rollback_da_unidade_de_trabalho_dentro_do_teste(conexao, fabrica_de_sessoes):
    await conexao.execute(text("CREATE TABLE exemplo_rollback (id integer PRIMARY KEY)"))
    unidade = UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes)

    with pytest.raises(RuntimeError):
        async with unidade:
            await unidade.sessao.execute(text("INSERT INTO exemplo_rollback (id) VALUES (1)"))
            raise RuntimeError("falha no meio da operação")

    assert await conexao.scalar(text("SELECT count(*) FROM exemplo_rollback")) == 0
