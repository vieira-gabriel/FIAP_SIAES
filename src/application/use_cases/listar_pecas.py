from domain.entities.estoque_peca import EstoquePeca
from domain.entities.peca import Peca
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.peca_repository import PecaRepository


class ListarPecas:
    """Peças ativas, em ordem de nome, com as quantidades do estoque; as excluídas ficam fora
    (RF-12)."""

    def __init__(self, pecas: PecaRepository, estoques: EstoqueRepository):
        self._pecas = pecas
        self._estoques = estoques

    async def executar(self) -> list[tuple[Peca, EstoquePeca]]:
        pecas = await self._pecas.listar()
        estoques = await self._estoques.buscar_por_pecas([peca.id for peca in pecas])
        return [(peca, estoques[peca.id]) for peca in pecas]
