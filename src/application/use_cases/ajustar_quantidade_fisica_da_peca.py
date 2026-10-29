from uuid import UUID

from application.events.event_dispatcher import EventDispatcher
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.peca import Peca
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.peca_repository import PecaRepository


class AjustarQuantidadeFisicaDaPeca:
    """Correção da quantidade física por perda, quebra ou inventário. Se o saldo aumentar, o
    evento é despachado na mesma transação (RF-12, RF-19, RNF-08)."""

    def __init__(
        self,
        pecas: PecaRepository,
        estoques: EstoqueRepository,
        eventos: EventDispatcher,
    ):
        self._pecas = pecas
        self._estoques = estoques
        self._eventos = eventos

    async def executar(self, id: UUID, nova_quantidade: int) -> tuple[Peca, EstoquePeca]:
        peca = await self._pecas.buscar_ativa_por_id(id)
        estoque = await self._estoques.buscar_por_peca(peca.id)
        estoque.ajustar_quantidade_fisica(nova_quantidade)
        await self._estoques.salvar(estoque)
        await self._eventos.despachar(estoque.collect_domain_events())
        return peca, estoque
