from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from domain.exceptions import AlocacaoInvalida, QuantidadeInvalida, ValorInvalido
from domain.value_objects.pendencia_peca import PendenciaPeca

ABERTURA = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def test_guarda_a_os_a_data_de_abertura_e_a_quantidade_pendente():
    os_id = uuid4()

    pendencia = PendenciaPeca(os_id=os_id, data_abertura_os=ABERTURA, quantidade_pendente=3)

    assert (pendencia.os_id, pendencia.data_abertura_os) == (os_id, ABERTURA)
    assert pendencia.quantidade_pendente == 3


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, "2", True, None])
def test_recusa_quantidade_que_nao_e_inteiro_positivo(quantidade):
    with pytest.raises(QuantidadeInvalida) as erro:
        PendenciaPeca(os_id=uuid4(), data_abertura_os=ABERTURA, quantidade_pendente=quantidade)

    assert isinstance(erro.value, ValorInvalido)


@pytest.mark.parametrize("os_id", ["nao-e-uuid", None, 123])
def test_recusa_os_que_nao_e_uuid(os_id):
    with pytest.raises(AlocacaoInvalida):
        PendenciaPeca(os_id=os_id, data_abertura_os=ABERTURA, quantidade_pendente=1)


@pytest.mark.parametrize(
    "data", [datetime(2026, 10, 1, 9, 0), "2026-10-01", None], ids=["sem fuso", "texto", "nula"]
)
def test_recusa_data_de_abertura_sem_fuso_horario_ou_que_nao_e_data(data):
    with pytest.raises(AlocacaoInvalida):
        PendenciaPeca(os_id=uuid4(), data_abertura_os=data, quantidade_pendente=1)


def test_pendencias_iguais_sao_iguais_e_o_objeto_e_imutavel():
    os_id = uuid4()
    uma = PendenciaPeca(os_id=os_id, data_abertura_os=ABERTURA, quantidade_pendente=2)
    outra = PendenciaPeca(os_id=os_id, data_abertura_os=ABERTURA, quantidade_pendente=2)

    assert uma == outra
    assert hash(uma) == hash(outra)
    with pytest.raises(FrozenInstanceError):
        uma.quantidade_pendente = 9
