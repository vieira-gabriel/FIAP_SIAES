from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


def _scripts() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))


def test_historico_de_migrations_tem_uma_unica_cabeca():
    assert len(_scripts().get_heads()) == 1


def test_historico_comeca_na_revisao_de_base_vazia():
    assert _scripts().get_bases() == ["0001"]
