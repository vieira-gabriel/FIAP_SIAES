from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from domain.events.domain_event import DomainEvent
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.value_objects.quantidade_peca import QuantidadePeca


def test_leva_a_os_e_as_quantidades_a_baixar_e_herda_a_base_dos_eventos():
    os_id = uuid4()
    baixas = [QuantidadePeca(uuid4(), 2), QuantidadePeca(uuid4(), 1)]

    evento = ExecucaoIniciadaEvent(os_id=os_id, baixas=baixas)

    assert isinstance(evento, DomainEvent)
    assert evento.os_id == os_id
    assert evento.baixas == baixas
    assert evento.event_id
    assert evento.occurred_on.tzinfo is not None


def test_exige_a_os_e_as_baixas():
    with pytest.raises(TypeError):
        ExecucaoIniciadaEvent()
    with pytest.raises(TypeError):
        ExecucaoIniciadaEvent(os_id=uuid4())


def test_e_imutavel():
    evento = ExecucaoIniciadaEvent(os_id=uuid4(), baixas=[])

    with pytest.raises(FrozenInstanceError):
        evento.baixas = [QuantidadePeca(uuid4(), 1)]
