from datetime import UTC, datetime

import pytest

from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.filtro_ordens_servico import FiltroOrdensServico

INICIO = datetime(2026, 10, 1, tzinfo=UTC)
FIM = datetime(2026, 10, 31, tzinfo=UTC)


def test_filtro_sem_criterios_e_valido():
    assert FiltroOrdensServico() == FiltroOrdensServico(status=None)


def test_periodo_com_fuso_horario_e_valido():
    filtro = FiltroOrdensServico(abertura_de=INICIO, abertura_ate=FIM)

    assert filtro.abertura_de == INICIO
    assert filtro.abertura_ate == FIM


@pytest.mark.parametrize(
    ("abertura_de", "abertura_ate"),
    [
        (datetime(2026, 10, 1), None),
        (None, datetime(2026, 10, 31)),
        (datetime(2026, 10, 1), FIM),
    ],
)
def test_periodo_sem_fuso_horario_e_recusado(abertura_de, abertura_ate):
    with pytest.raises(OrdemServicoInvalida, match="fuso horário"):
        FiltroOrdensServico(abertura_de=abertura_de, abertura_ate=abertura_ate)


def test_periodo_com_inicio_depois_do_fim_é_recusado():
    with pytest.raises(OrdemServicoInvalida, match="posterior ao fim"):
        FiltroOrdensServico(abertura_de=FIM, abertura_ate=INICIO)
