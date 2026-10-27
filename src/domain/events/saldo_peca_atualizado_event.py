from dataclasses import dataclass
from uuid import UUID

from domain.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class SaldoPecaAtualizadoEvent(DomainEvent):
    """O saldo disponível da peça aumentou, e as OS com peça pendente podem ser atendidas.

    Emitido por `EstoquePeca` em toda reposição, estorno ou ajuste que aumenta o saldo (RF-12,
    RF-19).
    """

    peca_id: UUID
    saldo_disponivel: int
