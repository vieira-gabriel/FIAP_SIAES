from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Iterable

from domain.events.domain_event import DomainEvent


class EventHandler[E: DomainEvent](ABC):
    @abstractmethod
    async def tratar(self, evento: E) -> list[DomainEvent]:
        """Reage ao evento e devolve os eventos que os agregados alterados emitiram."""


class EventDispatcher:
    """Despacho síncrono, em memória, dos eventos de domínio (catálogo, seção 7; RNF-08).

    O caso de uso chama `despachar` dentro do bloco da unidade de trabalho. Uma exceção de
    handler interrompe o despacho e sobe até o bloco, que desfaz a transação inteira.
    """

    def __init__(self):
        self._handlers: defaultdict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def registrar[E: DomainEvent](self, tipo_evento: type[E], handler: EventHandler[E]) -> None:
        self._handlers[tipo_evento].append(handler)

    async def despachar(self, eventos: Iterable[DomainEvent]) -> None:
        """Os eventos devolvidos pelos handlers entram no fim da fila, até não restar nenhum.

        Um estorno, por exemplo, gera `SaldoPecaAtualizadoEvent`, que também é despachado.
        """
        fila = deque(eventos)
        while fila:
            evento = fila.popleft()
            for handler in self._handlers[type(evento)]:
                fila.extend(await handler.tratar(evento))
