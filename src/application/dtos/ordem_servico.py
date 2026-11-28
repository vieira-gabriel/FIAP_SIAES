from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.value_objects.documento import Documento
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS


@dataclass(frozen=True)
class CriteriosDaListagem:
    """Critérios como chegam da requisição, antes de documento e placa virarem identificadores."""

    documento: Documento | None = None
    placa: Placa | None = None
    status: StatusOS | None = None
    mecanico_id: UUID | None = None
    abertura_de: datetime | None = None
    abertura_ate: datetime | None = None


@dataclass(frozen=True)
class ResumoDaOrdemServico:
    os: OrdemServico
    cliente: Cliente
    veiculo: Veiculo
    mecanico: Usuario | None


@dataclass(frozen=True)
class DetalheDaOrdemServico:
    os: OrdemServico
    cliente: Cliente
    veiculo: Veiculo
    estimativa_entrega: datetime | None
