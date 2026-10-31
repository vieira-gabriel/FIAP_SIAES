from typing import Any, cast

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

_SQLSTATE_IMPASSE = "40P01"
_TENTATIVAS = 3


def _e_impasse(erro: DBAPIError) -> bool:
    return getattr(erro.orig, "sqlstate", None) == _SQLSTATE_IMPASSE


class _CasoDeUsoComRepeticao:
    def __init__(self, caso_de_uso: Any, sessao: AsyncSession):
        self._caso_de_uso = caso_de_uso
        self._sessao = sessao

    async def executar(self, *args: Any, **kwargs: Any) -> Any:
        for tentativa in range(1, _TENTATIVAS + 1):
            try:
                return await self._caso_de_uso.executar(*args, **kwargs)
            except DBAPIError as erro:
                if not _e_impasse(erro) or tentativa == _TENTATIVAS:
                    raise
                await self._sessao.rollback()


def com_repeticao_em_impasse[C](caso_de_uso: C, sessao: AsyncSession) -> C:
    """Repete o caso de uso quando o PostgreSQL aborta a transação por impasse (deadlock).

    A alocação das peças repostas bloqueia o estoque e depois as OS, e o cancelamento bloqueia a OS
    e depois o estoque (RF-19, RF-23). Se as duas se cruzarem, o banco aborta uma delas, e a
    repetição refaz as leituras e as gravações do zero, na mesma sessão (RNF-08, RNF-09).
    """
    return cast(C, _CasoDeUsoComRepeticao(caso_de_uso, sessao))
