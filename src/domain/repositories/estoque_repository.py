from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID

from domain.entities.estoque_peca import EstoquePeca


class EstoqueRepository(ABC):
    @abstractmethod
    async def salvar(self, estoque: EstoquePeca) -> None: ...

    @abstractmethod
    async def buscar_por_peca(self, peca_id: UUID) -> EstoquePeca | None:
        """Bloqueia o estoque até o fim da transação, para duas operações não disputarem o mesmo
        saldo (RNF-09). Use só quando a operação vai alterar o estoque."""

    @abstractmethod
    async def buscar_por_pecas(self, peca_ids: Collection[UUID]) -> dict[UUID, EstoquePeca]:
        """Leitura sem bloqueio, para consulta; as peças sem estoque ficam fora do dicionário."""
