from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.status_os import StatusOS


@dataclass(frozen=True)
class FiltroOrdensServico:
    """Critérios combináveis da listagem de OS (RF-14). Um critério não informado não filtra."""

    status: StatusOS | None = None
    mecanico_id: UUID | None = None
    cliente_id: UUID | None = None
    veiculo_id: UUID | None = None
    abertura_de: datetime | None = None
    abertura_ate: datetime | None = None

    def __post_init__(self):
        for momento in (self.abertura_de, self.abertura_ate):
            if momento is not None and momento.tzinfo is None:
                raise OrdemServicoInvalida("o período de abertura precisa ter fuso horário")
        if self.abertura_de is not None and self.abertura_ate is not None:
            if self.abertura_de > self.abertura_ate:
                raise OrdemServicoInvalida("o início do período é posterior ao fim")
