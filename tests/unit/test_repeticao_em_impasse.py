import pytest
from sqlalchemy.exc import DBAPIError

from infrastructure.database.repeticao_em_impasse import com_repeticao_em_impasse


class ErroDoDriver(Exception):
    def __init__(self, sqlstate: str | None):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _erro(sqlstate: str | None) -> DBAPIError:
    return DBAPIError("SELECT 1", None, ErroDoDriver(sqlstate))


class SessaoEspia:
    def __init__(self):
        self.desfeitas = 0

    async def rollback(self):
        self.desfeitas += 1


class CasoDeUsoQueFalha:
    def __init__(self, *falhas: Exception):
        self._falhas = list(falhas)
        self.chamadas: list[tuple] = []

    async def executar(self, *args, **kwargs):
        self.chamadas.append((args, kwargs))
        if self._falhas:
            raise self._falhas.pop(0)
        return "ok"


async def test_sem_falha_executa_uma_vez_e_devolve_o_resultado():
    caso, sessao = CasoDeUsoQueFalha(), SessaoEspia()

    resultado = await com_repeticao_em_impasse(caso, sessao).executar(1, chave=2)

    assert (resultado, caso.chamadas, sessao.desfeitas) == ("ok", [((1,), {"chave": 2})], 0)


async def test_repete_depois_de_desfazer_a_transacao_quando_ha_impasse():
    caso, sessao = CasoDeUsoQueFalha(_erro("40P01"), _erro("40P01")), SessaoEspia()

    resultado = await com_repeticao_em_impasse(caso, sessao).executar()

    assert (resultado, len(caso.chamadas), sessao.desfeitas) == ("ok", 3, 2)


async def test_na_terceira_falha_propaga_o_impasse():
    caso = CasoDeUsoQueFalha(_erro("40P01"), _erro("40P01"), _erro("40P01"))
    sessao = SessaoEspia()

    with pytest.raises(DBAPIError):
        await com_repeticao_em_impasse(caso, sessao).executar()

    assert (len(caso.chamadas), sessao.desfeitas) == (3, 2)


@pytest.mark.parametrize("sqlstate", ["23505", None])
async def test_outro_erro_do_banco_sobe_sem_repetir(sqlstate):
    caso, sessao = CasoDeUsoQueFalha(_erro(sqlstate)), SessaoEspia()

    with pytest.raises(DBAPIError):
        await com_repeticao_em_impasse(caso, sessao).executar()

    assert (len(caso.chamadas), sessao.desfeitas) == (1, 0)


async def test_erro_que_nao_e_do_banco_sobe_sem_repetir():
    caso, sessao = CasoDeUsoQueFalha(RuntimeError("falha")), SessaoEspia()

    with pytest.raises(RuntimeError):
        await com_repeticao_em_impasse(caso, sessao).executar()

    assert len(caso.chamadas) == 1
