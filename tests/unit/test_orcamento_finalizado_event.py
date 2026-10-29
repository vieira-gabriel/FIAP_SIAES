from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from domain.events.domain_event import DomainEvent
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent


def test_leva_a_os_e_herda_a_base_dos_eventos():
    os_id = uuid4()

    evento = OrcamentoFinalizadoEvent(os_id=os_id)

    assert isinstance(evento, DomainEvent)
    assert evento.os_id == os_id
    assert evento.event_id
    assert evento.occurred_on.tzinfo is not None


def test_exige_a_os():
    with pytest.raises(TypeError):
        OrcamentoFinalizadoEvent()


def test_e_imutavel():
    evento = OrcamentoFinalizadoEvent(os_id=uuid4())

    with pytest.raises(FrozenInstanceError):
        evento.os_id = uuid4()
