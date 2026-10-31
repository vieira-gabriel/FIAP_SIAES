from application.events.event_dispatcher import EventHandler
from domain.events.domain_event import DomainEvent
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.estoque_repository import EstoqueRepository


class EstornoReservasHandler(EventHandler[OSCanceladaEvent]):
    """Devolve ao saldo as peças que a OS cancelada tinha reservadas (RF-18, RF-23).

    Roda na transação do cancelamento, com a OS já bloqueada, e bloqueia o estoque de cada peça
    em ordem de id. O saldo devolvido gera `SaldoPecaAtualizadoEvent`, que o despacho entrega à
    alocação às OS que esperam a peça (RF-19). As pendências da OS já foram descartadas por ela.
    """

    def __init__(self, estoques: EstoqueRepository):
        self._estoques = estoques

    async def tratar(self, evento: OSCanceladaEvent) -> list[DomainEvent]:
        eventos: list[DomainEvent] = []
        for estorno in sorted(evento.estornos, key=lambda estorno: estorno.peca_id):
            estoque = await self._estoques.buscar_por_peca(estorno.peca_id)
            if estoque is None:
                raise EntidadeNaoEncontrada("Estoque da peça", estorno.peca_id)
            estoque.estornar(estorno.quantidade)
            await self._estoques.salvar(estoque)
            eventos.extend(estoque.collect_domain_events())
        return eventos
