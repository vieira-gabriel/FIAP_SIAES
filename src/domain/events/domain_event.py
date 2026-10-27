from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base dos eventos de domínio, despachados pelo `EventDispatcher` (catálogo, seção 7).

    `kw_only` permite que cada evento declare campos obrigatórios, como `os_id`, mesmo com os
    campos da base tendo valor padrão.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_on: datetime = field(default_factory=lambda: datetime.now(UTC))
