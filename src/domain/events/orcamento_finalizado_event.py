from dataclasses import dataclass
from uuid import UUID

from domain.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrcamentoFinalizadoEvent(DomainEvent):
    """A OS concluiu o orçamento, e as peças dela devem ser reservadas (RF-17, RF-18).

    Emitido por `OrdemServico.finalizar_orcamento`. A quantidade de cada peça da OS nasce toda
    pendente, e quem reage ao evento busca a OS pelo `os_id`.
    """

    os_id: UUID
