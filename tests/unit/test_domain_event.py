from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from domain.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class EventoComCampoObrigatorio(DomainEvent):
    os_id: UUID


def test_gera_identificador_unico_para_cada_evento():
    assert DomainEvent().event_id != DomainEvent().event_id


def test_registra_o_momento_da_ocorrencia_em_utc():
    antes = datetime.now(UTC)

    ocorrido = DomainEvent().occurred_on

    assert ocorrido.tzinfo is UTC
    assert antes <= ocorrido <= antes + timedelta(seconds=1)


def test_evento_derivado_declara_campo_obrigatorio_sem_valor_padrao():
    os_id = uuid4()

    evento = EventoComCampoObrigatorio(os_id=os_id)

    assert evento.os_id == os_id
    assert evento.event_id

    with pytest.raises(TypeError):
        EventoComCampoObrigatorio()


def test_e_imutavel():
    evento = DomainEvent()

    with pytest.raises(FrozenInstanceError):
        evento.event_id = "outro"
