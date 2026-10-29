from dataclasses import dataclass
from uuid import UUID

from domain.events.domain_event import DomainEvent
from domain.value_objects.quantidade_peca import QuantidadePeca


@dataclass(frozen=True, kw_only=True)
class ExecucaoIniciadaEvent(DomainEvent):
    """A execução da OS começou, e as peças reservadas devem receber baixa (RF-20).

    Emitido por `OrdemServico.iniciar_execucao`, com a quantidade reservada de cada peça.
    """

    os_id: UUID
    baixas: list[QuantidadePeca]
