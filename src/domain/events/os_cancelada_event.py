from dataclasses import dataclass
from uuid import UUID

from domain.events.domain_event import DomainEvent
from domain.value_objects.quantidade_peca import QuantidadePeca


@dataclass(frozen=True, kw_only=True)
class OSCanceladaEvent(DomainEvent):
    """A OS foi cancelada, e as reservas dela devem voltar ao estoque (RF-18, RF-23, RF-26).

    Emitido por `OrdemServico.rejeitar_orcamento` e `OrdemServico.cancelar`. Os `estornos` vêm
    calculados pela OS: ficam vazios quando ela é cancelada em `EM_EXECUCAO`, porque a baixa
    das peças já ocorreu no início da execução.
    """

    os_id: UUID
    estornos: list[QuantidadePeca]
