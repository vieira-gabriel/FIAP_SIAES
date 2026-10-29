from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from domain.events.domain_event import DomainEvent
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.value_objects.quantidade_peca import QuantidadePeca


def test_leva_a_os_e_as_quantidades_a_estornar_e_herda_a_base_dos_eventos():
    os_id = uuid4()
    estornos = [QuantidadePeca(uuid4(), 2)]

    evento = OSCanceladaEvent(os_id=os_id, estornos=estornos)

    assert isinstance(evento, DomainEvent)
    assert evento.os_id == os_id
    assert evento.estornos == estornos
    assert evento.event_id
    assert evento.occurred_on.tzinfo is not None


def test_aceita_estornos_vazios():
    assert OSCanceladaEvent(os_id=uuid4(), estornos=[]).estornos == []


def test_exige_a_os_e_os_estornos():
    with pytest.raises(TypeError):
        OSCanceladaEvent()
    with pytest.raises(TypeError):
        OSCanceladaEvent(os_id=uuid4())


def test_e_imutavel():
    evento = OSCanceladaEvent(os_id=uuid4(), estornos=[])

    with pytest.raises(FrozenInstanceError):
        evento.estornos = [QuantidadePeca(uuid4(), 1)]
