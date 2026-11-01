from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS

ABERTURA = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
USUARIO = uuid4()


def _horas(horas: float) -> timedelta:
    return timedelta(hours=horas)


def _historico(*etapas: tuple[StatusOS, timedelta]) -> tuple[HistoricoStatusOS, ...]:
    registros, anterior = [], None
    for status, depois_da_abertura in etapas:
        registros.append(
            HistoricoStatusOS(
                anterior,
                status,
                ABERTURA + depois_da_abertura,
                OrigemTransicao.USUARIO if anterior else OrigemTransicao.SISTEMA,
                USUARIO if anterior else None,
            )
        )
        anterior = status
    return tuple(registros)


def _os(*etapas: tuple[StatusOS, timedelta], **datas) -> OrdemServico:
    return OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=etapas[-1][0],
        data_abertura=ABERTURA,
        historico=_historico(*etapas),
        **datas,
    )


def _finalizada_sem_espera() -> OrdemServico:
    return _os(
        (StatusOS.RECEBIDA, _horas(0)),
        (StatusOS.EM_DIAGNOSTICO, _horas(1)),
        (StatusOS.AGUARDANDO_APROVACAO, _horas(2)),
        (StatusOS.AGUARDANDO_EXECUCAO, _horas(3)),
        (StatusOS.EM_EXECUCAO, _horas(4)),
        (StatusOS.FINALIZADA, _horas(10)),
        data_inicio_execucao=ABERTURA + _horas(4),
        data_finalizacao=ABERTURA + _horas(10),
    )


def _finalizada_com_espera() -> OrdemServico:
    return _os(
        (StatusOS.RECEBIDA, _horas(0)),
        (StatusOS.EM_DIAGNOSTICO, _horas(1)),
        (StatusOS.AGUARDANDO_APROVACAO, _horas(2)),
        (StatusOS.AGUARDANDO_PECA, _horas(3)),
        (StatusOS.AGUARDANDO_EXECUCAO, _horas(8)),
        (StatusOS.EM_EXECUCAO, _horas(9)),
        (StatusOS.FINALIZADA, _horas(12)),
        data_inicio_execucao=ABERTURA + _horas(9),
        data_finalizacao=ABERTURA + _horas(12),
    )


def test_tempo_de_execucao_vai_do_inicio_da_execucao_a_finalizacao():
    assert _finalizada_sem_espera().tempo_de_execucao() == _horas(6)
    assert _finalizada_com_espera().tempo_de_execucao() == _horas(3)


def test_tempo_total_vai_da_abertura_a_finalizacao_com_as_esperas():
    assert _finalizada_sem_espera().tempo_total() == _horas(10)
    assert _finalizada_com_espera().tempo_total() == _horas(12)


def test_tempo_de_espera_por_peca_vai_da_entrada_a_saida_de_aguardando_peca():
    assert _finalizada_com_espera().tempo_de_espera_por_peca() == _horas(5)


def test_sem_passagem_por_aguardando_peca_a_espera_e_nula():
    assert _finalizada_sem_espera().tempo_de_espera_por_peca() is None


def test_espera_em_andamento_nao_conta():
    os = _os(
        (StatusOS.RECEBIDA, _horas(0)),
        (StatusOS.EM_DIAGNOSTICO, _horas(1)),
        (StatusOS.AGUARDANDO_APROVACAO, _horas(2)),
        (StatusOS.AGUARDANDO_PECA, _horas(3)),
    )

    assert os.tempo_de_espera_por_peca() is None


def test_varias_esperas_somam():
    os = _os(
        (StatusOS.RECEBIDA, _horas(0)),
        (StatusOS.EM_DIAGNOSTICO, _horas(1)),
        (StatusOS.AGUARDANDO_APROVACAO, _horas(2)),
        (StatusOS.AGUARDANDO_PECA, _horas(3)),
        (StatusOS.AGUARDANDO_EXECUCAO, _horas(4)),
        (StatusOS.AGUARDANDO_PECA, _horas(6)),
        (StatusOS.AGUARDANDO_EXECUCAO, _horas(9)),
    )

    assert os.tempo_de_espera_por_peca() == _horas(4)


def test_execucao_e_total_exigem_a_os_finalizada():
    os = _os((StatusOS.RECEBIDA, _horas(0)))

    with pytest.raises(OrdemServicoInvalida):
        os.tempo_de_execucao()
    with pytest.raises(OrdemServicoInvalida):
        os.tempo_total()
