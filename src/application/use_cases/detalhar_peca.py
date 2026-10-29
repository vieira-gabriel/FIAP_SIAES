from uuid import UUID

from domain.entities.estoque_peca import EstoquePeca
from domain.entities.peca import Peca
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.peca_repository import PecaRepository


class DetalharPeca:
    """Consulta de uma peça ativa com as quantidades do estoque (RF-12)."""

    def __init__(self, pecas: PecaRepository, estoques: EstoqueRepository):
        self._pecas = pecas
        self._estoques = estoques

    async def executar(self, id: UUID) -> tuple[Peca, EstoquePeca]:
        peca = await self._pecas.buscar_ativa_por_id(id)
        estoques = await self._estoques.buscar_por_pecas([peca.id])
        return peca, estoques[peca.id]
