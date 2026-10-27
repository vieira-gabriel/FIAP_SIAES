from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS


@dataclass(frozen=True)
class HistoricoStatusOS:
    """Registro imutável de uma transição de status da OS (RF-24).

    Sem `status_anterior`, é o registro da abertura. O `usuario_id` só existe quando a origem
    é `USUARIO`.
    """

    status_anterior: StatusOS | None
    status_novo: StatusOS
    data_hora: datetime
    origem: OrigemTransicao
    usuario_id: UUID | None = None
    motivo: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        if self.status_anterior is not None and not isinstance(self.status_anterior, StatusOS):
            raise OrdemServicoInvalida("o status anterior do histórico é inválido")
        if not isinstance(self.status_novo, StatusOS):
            raise OrdemServicoInvalida("o novo status do histórico é obrigatório")
        if self.status_anterior == self.status_novo:
            raise OrdemServicoInvalida("o novo status deve ser diferente do anterior")
        if not isinstance(self.data_hora, datetime):
            raise OrdemServicoInvalida("a data e hora do histórico são obrigatórias")
        if not isinstance(self.origem, OrigemTransicao):
            raise OrdemServicoInvalida("a origem da transição é obrigatória")
        if self.origem is OrigemTransicao.USUARIO and not isinstance(self.usuario_id, UUID):
            raise OrdemServicoInvalida("a transição feita por um usuário exige o usuário")
        if self.origem is not OrigemTransicao.USUARIO and self.usuario_id is not None:
            raise OrdemServicoInvalida("só a transição feita por um usuário informa o usuário")
        object.__setattr__(self, "motivo", _normalizar(self.motivo))


def _normalizar(motivo: str | None) -> str | None:
    if motivo is None:
        return None
    if not isinstance(motivo, str):
        raise OrdemServicoInvalida("o motivo do histórico deve ser um texto")
    return motivo.strip() or None
