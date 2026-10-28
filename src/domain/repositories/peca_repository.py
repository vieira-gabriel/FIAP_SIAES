from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.peca import Peca


class PecaRepository(ABC):
    @abstractmethod
    async def salvar(self, peca: Peca) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Peca | None: ...

    @abstractmethod
    async def buscar_por_codigo_referencia(self, codigo_referencia: str) -> Peca | None:
        """Também encontra a peça excluída, porque o código continua reservado a ela."""

    @abstractmethod
    async def listar(self) -> list[Peca]:
        """Só as peças ativas, em ordem de nome (RF-12)."""
