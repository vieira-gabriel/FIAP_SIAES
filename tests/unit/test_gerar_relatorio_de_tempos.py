from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application.use_cases.gerar_relatorio_de_tempos import (
    GerarRelatorioDeTempos,
    TempoMedio,
    TempoMedioDoMecanico,
)
from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.status_os import StatusOS

OUTUBRO = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
NOVEMBRO = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)


@pytest.fixture
def gerar(ordens, usuarios) -> GerarRelatorioDeTempos:
    return GerarRelatorioDeTempos(ordens, usuarios)


def _novo_mecanico(nome: str) -> Usuario:
    return Usuario(
        nome=nome,
        email=f"{uuid4().hex[:8]}@oficina.com",
        senha_hash="h",
        perfil=PerfilUsuario.MECANICO,
    )


async def _mecanico(usuarios, nome: str) -> Usuario:
    mecanico = _novo_mecanico(nome)
    await usuarios.salvar(mecanico)
    return mecanico


def _finalizada(
    mecanico: Usuario,
    abertura: datetime,
    *,
    espera_horas: int | None,
    execucao_horas: int,
    numero: str,
) -> OrdemServico:
    """Abertura, 1 h de diagnóstico, espera opcional por peça e a execução até a finalização."""
    diagnostico = abertura + timedelta(hours=1)
    etapas = [(StatusOS.RECEBIDA, abertura), (StatusOS.EM_DIAGNOSTICO, diagnostico)]
    inicio = diagnostico
    if espera_horas is not None:
        etapas.append((StatusOS.AGUARDANDO_PECA, diagnostico))
        inicio += timedelta(hours=espera_horas)
    fim = inicio + timedelta(hours=execucao_horas)
    etapas += [(StatusOS.EM_EXECUCAO, inicio), (StatusOS.FINALIZADA, fim)]
    historico, anterior = [], None
    for status, data_hora in etapas:
        historico.append(
            HistoricoStatusOS(
                anterior,
                status,
                data_hora,
                OrigemTransicao.USUARIO if anterior else OrigemTransicao.SISTEMA,
                mecanico.id if anterior else None,
            )
        )
        anterior = status
    return OrdemServico(
        numero=NumeroOS(numero),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        mecanico_id=mecanico.id,
        status=StatusOS.FINALIZADA,
        data_abertura=abertura,
        data_inicio_execucao=inicio,
        data_finalizacao=fim,
        historico=tuple(historico),
    )


async def _cenario(ordens, usuarios) -> tuple[Usuario, Usuario]:
    """Outubro: Ana executa em 2 h e em 4 h (esta esperou 3 h por peça) e Bruno em 6 h.
    Novembro: Bruno executa em 8 h, depois de 5 h de espera."""
    ana = await _mecanico(usuarios, "Ana")
    bruno = await _mecanico(usuarios, "Bruno")
    for os in (
        _finalizada(ana, OUTUBRO, espera_horas=None, execucao_horas=2, numero="529-00000001"),
        _finalizada(ana, OUTUBRO, espera_horas=3, execucao_horas=4, numero="529-00000002"),
        _finalizada(bruno, OUTUBRO, espera_horas=None, execucao_horas=6, numero="529-00000003"),
        _finalizada(bruno, NOVEMBRO, espera_horas=5, execucao_horas=8, numero="529-00000004"),
    ):
        await ordens.salvar(os)
    return ana, bruno


async def test_execucao_e_media_por_mes_e_por_mecanico(gerar, ordens, usuarios):
    ana, bruno = await _cenario(ordens, usuarios)

    relatorio = await gerar.executar()

    assert relatorio.execucao == [
        TempoMedioDoMecanico("2026-10", ana.id, "Ana", 2, timedelta(hours=3)),
        TempoMedioDoMecanico("2026-10", bruno.id, "Bruno", 1, timedelta(hours=6)),
        TempoMedioDoMecanico("2026-11", bruno.id, "Bruno", 1, timedelta(hours=8)),
    ]


async def test_espera_por_peca_e_media_so_das_os_que_esperaram(gerar, ordens, usuarios):
    await _cenario(ordens, usuarios)

    relatorio = await gerar.executar()

    assert relatorio.espera_por_peca == [
        TempoMedio("2026-10", 1, timedelta(hours=3)),
        TempoMedio("2026-11", 1, timedelta(hours=5)),
    ]


async def test_tempo_total_inclui_as_esperas(gerar, ordens, usuarios):
    await _cenario(ordens, usuarios)

    relatorio = await gerar.executar()

    # Outubro: 3 h, 8 h e 7 h (média de 6 h). Novembro: 1 + 5 + 8 = 14 h.
    assert relatorio.total == [
        TempoMedio("2026-10", 3, timedelta(hours=6)),
        TempoMedio("2026-11", 1, timedelta(hours=14)),
    ]


async def test_o_periodo_filtra_pela_data_de_finalizacao(gerar, ordens, usuarios):
    await _cenario(ordens, usuarios)

    relatorio = await gerar.executar(finalizadas_de=datetime(2026, 11, 1, tzinfo=UTC))

    assert [t.periodo for t in relatorio.total] == ["2026-11"]


async def test_os_nao_finalizada_fica_fora(gerar, ordens):
    await ordens.salvar(
        OrdemServico(
            numero=NumeroOS("529-00000009"),
            cliente_id=uuid4(),
            veiculo_id=uuid4(),
            atendente_id=uuid4(),
        )
    )

    relatorio = await gerar.executar()

    assert (relatorio.execucao, relatorio.espera_por_peca, relatorio.total) == ([], [], [])


async def test_mecanico_nao_encontrado_fica_sem_nome(gerar, ordens):
    ana = _novo_mecanico("Ana")
    await ordens.salvar(
        _finalizada(ana, OUTUBRO, espera_horas=None, execucao_horas=2, numero="529-00000001")
    )

    relatorio = await gerar.executar()

    assert relatorio.execucao[0].mecanico_nome is None


@pytest.mark.parametrize(
    ("de", "ate"),
    [
        (datetime(2026, 10, 1), None),
        (None, datetime(2026, 10, 1)),
        (datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)),
    ],
)
async def test_periodo_sem_fuso_ou_invertido_e_recusado(gerar, de, ate):
    with pytest.raises(OrdemServicoInvalida):
        await gerar.executar(de, ate)
