"""Relatório de tempos médios pela rota HTTP, com PostgreSQL real (RF-27, RF-24, RNF-13)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.status_os import StatusOS
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_ordem_servico_repository import (
    PostgresOrdemServicoRepository,
)
from presentation.main import app

ABERTURA = {
    "documento": "529.982.247-25",
    "placa": "ABC1D23",
    "cliente": {"nome": "Maria Silva", "email": "maria@exemplo.com", "telefone": "11987654321"},
    "veiculo": {"marca": "Fiat", "modelo": "Uno", "ano": 2015},
}
OUTUBRO = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
NOVEMBRO = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
HORA = 3600


async def _inserir_usuario(conexao, perfil: PerfilUsuario, nome: str | None = None) -> Usuario:
    usuario = Usuario(
        nome=nome or perfil.value.title(),
        email=f"{perfil.value.lower()}-{uuid4().hex[:8]}@oficina.com",
        senha_hash="hash",
        perfil=perfil,
    )
    await conexao.execute(
        text(
            "INSERT INTO usuarios (id, nome, email, senha_hash, perfil, ativo) "
            "VALUES (:id, :nome, :email, :senha_hash, :perfil, true)"
        ),
        {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "senha_hash": usuario.senha_hash,
            "perfil": perfil.value,
        },
    )
    return usuario


def _cabecalho(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.state.token_service.emitir(usuario)}"}


@pytest.fixture
async def atendente(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.ATENDENTE)


@pytest.fixture
async def mecanico(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.MECANICO)


@pytest.fixture
async def gerente(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.GERENTE)


def _finalizada(
    base: OrdemServico,
    mecanico: Usuario,
    abertura: datetime,
    *,
    espera_horas: int | None,
    execucao_horas: int,
) -> OrdemServico:
    """OS com 1 h de diagnóstico, espera opcional por peça e a execução até a finalização."""
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
    os_id = uuid4()
    return OrdemServico(
        id=os_id,
        numero=NumeroOS(f"529-{os_id.hex[:8].upper()}"),
        cliente_id=base.cliente_id,
        veiculo_id=base.veiculo_id,
        atendente_id=base.atendente_id,
        mecanico_id=mecanico.id,
        status=StatusOS.FINALIZADA,
        data_abertura=abertura,
        data_inicio_execucao=inicio,
        data_finalizacao=fim,
        historico=tuple(historico),
    )


@pytest.fixture
async def cenario(cliente_http, atendente, conexao, fabrica_de_sessoes):
    """Mesmo cenário do teste unitário, gravado no banco.

    Outubro: o mecânico Ana executa em 2 h e em 4 h (esta esperou 3 h por peça) e Bruno em 6 h.
    Novembro: Bruno executa em 8 h, depois de 5 h de espera.
    """
    aberta = (
        await cliente_http.post("/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente))
    ).json()
    base = OrdemServico(
        numero=NumeroOS(aberta["numero"]),
        id=UUID(aberta["id"]),
        cliente_id=UUID(aberta["cliente_id"]),
        veiculo_id=UUID(aberta["veiculo_id"]),
        atendente_id=atendente.id,
    )
    ana = await _inserir_usuario(conexao, PerfilUsuario.MECANICO, "Ana")
    bruno = await _inserir_usuario(conexao, PerfilUsuario.MECANICO, "Bruno")
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)
        for mecanico_da_os, abertura, espera, execucao in (
            (ana, OUTUBRO, None, 2),
            (ana, OUTUBRO, 3, 4),
            (bruno, OUTUBRO, None, 6),
            (bruno, NOVEMBRO, 5, 8),
        ):
            await ordens.salvar(
                _finalizada(
                    base, mecanico_da_os, abertura, espera_horas=espera, execucao_horas=execucao
                )
            )
    return {"ana": ana, "bruno": bruno}


async def _relatorio(cliente_http, gerente, **periodo):
    return await cliente_http.get(
        "/relatorios/tempos-medios", params=periodo, headers=_cabecalho(gerente)
    )


async def test_medias_de_execucao_por_mes_e_por_mecanico(cliente_http, gerente, cenario):
    resposta = await _relatorio(cliente_http, gerente)

    assert resposta.status_code == 200
    assert [
        (t["periodo"], t["mecanico_nome"], t["quantidade_os"], t["tempo_medio_segundos"])
        for t in resposta.json()["execucao"]
    ] == [
        ("2026-10", "Ana", 2, 3 * HORA),
        ("2026-10", "Bruno", 1, 6 * HORA),
        ("2026-11", "Bruno", 1, 8 * HORA),
    ]


async def test_media_de_espera_por_peca_so_das_os_que_esperaram(cliente_http, gerente, cenario):
    resposta = await _relatorio(cliente_http, gerente)

    assert resposta.json()["espera_por_peca"] == [
        {"periodo": "2026-10", "quantidade_os": 1, "tempo_medio_segundos": 3 * HORA},
        {"periodo": "2026-11", "quantidade_os": 1, "tempo_medio_segundos": 5 * HORA},
    ]


async def test_media_do_tempo_total_inclui_as_esperas(cliente_http, gerente, cenario):
    resposta = await _relatorio(cliente_http, gerente)

    assert resposta.json()["total"] == [
        {"periodo": "2026-10", "quantidade_os": 3, "tempo_medio_segundos": 6 * HORA},
        {"periodo": "2026-11", "quantidade_os": 1, "tempo_medio_segundos": 14 * HORA},
    ]


async def test_o_periodo_filtra_pela_data_de_finalizacao(cliente_http, gerente, cenario):
    resposta = await _relatorio(
        cliente_http,
        gerente,
        finalizadas_de="2026-11-01T00:00:00+00:00",
        finalizadas_ate="2026-11-30T23:59:59+00:00",
    )

    assert [t["periodo"] for t in resposta.json()["total"]] == ["2026-11"]


async def test_os_que_nao_foi_finalizada_nao_entra(cliente_http, gerente, atendente):
    await cliente_http.post("/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente))

    resposta = await _relatorio(cliente_http, gerente)

    assert resposta.json() == {"execucao": [], "espera_por_peca": [], "total": []}


@pytest.mark.parametrize(
    "periodo",
    [
        {"finalizadas_de": "2026-10-01T00:00:00"},
        {
            "finalizadas_de": "2026-11-01T00:00:00+00:00",
            "finalizadas_ate": "2026-10-01T00:00:00+00:00",
        },
    ],
)
async def test_periodo_sem_fuso_ou_invertido_responde_400(cliente_http, gerente, periodo):
    resposta = await _relatorio(cliente_http, gerente, **periodo)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_atendente_recebe_403(cliente_http, atendente):
    resposta = await _relatorio(cliente_http, atendente)

    assert resposta.status_code == 403


async def test_mecanico_recebe_403(cliente_http, mecanico):
    resposta = await _relatorio(cliente_http, mecanico)

    assert resposta.status_code == 403
