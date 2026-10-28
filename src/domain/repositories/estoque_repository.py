from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.estoque_peca import EstoquePeca


class EstoqueRepository(ABC):
    @abstractmethod
    async def salvar(self, estoque: EstoquePeca) -> None: ...

    @abstractmethod
    async def buscar_por_peca(self, peca_id: UUID) -> EstoquePeca | None: ...
