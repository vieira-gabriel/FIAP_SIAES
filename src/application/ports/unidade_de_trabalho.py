from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class UnidadeDeTrabalho(ABC):
    """Agrupa as escritas de uma operação crítica em uma única transação (RNF-08).

    Usada como `async with`: ao sair do bloco sem exceção, confirma tudo; com qualquer exceção,
    desfaz tudo e a propaga. As implementações abrem e liberam os recursos técnicos (sessão).
    """

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        tipo_excecao: type[BaseException] | None,
        excecao: BaseException | None,
        rastreamento: TracebackType | None,
    ) -> None:
        if tipo_excecao is not None:
            await self.desfazer()
            return
        try:
            await self.confirmar()
        except Exception:
            await self.desfazer()
            raise

    @abstractmethod
    async def confirmar(self) -> None: ...

    @abstractmethod
    async def desfazer(self) -> None: ...
