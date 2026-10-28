from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from domain.events.domain_event import DomainEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent


def test_leva_a_peca_e_o_saldo_disponivel_e_herda_a_base_dos_eventos():
    peca_id = uuid4()

    evento = SaldoPecaAtualizadoEvent(peca_id=peca_id, saldo_disponivel=7)

    assert isinstance(evento, DomainEvent)
    assert evento.peca_id == peca_id
    assert evento.saldo_disponivel == 7
    assert evento.event_id
    assert evento.occurred_on.tzinfo is not None


def test_exige_a_peca_e_o_saldo():
    with pytest.raises(TypeError):
        SaldoPecaAtualizadoEvent()
    with pytest.raises(TypeError):
        SaldoPecaAtualizadoEvent(peca_id=uuid4())


def test_e_imutavel():
    evento = SaldoPecaAtualizadoEvent(peca_id=uuid4(), saldo_disponivel=1)

    with pytest.raises(FrozenInstanceError):
        evento.saldo_disponivel = 99
