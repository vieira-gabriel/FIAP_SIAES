"""Listagem das OS pela rota HTTP, com PostgreSQL real (RF-14, RNF-13)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_ordem_servico_repository import (
    PostgresOrdemServicoRepository,
)
from presentation.main import app

CPF_MARIA = "529.982.247-25"
CPF_JOSE = "111.444.777-35"
CPF_SEM_CADASTRO = "123.456.789-09"
VEICULO = {"marca": "Fiat", "modelo": "Uno", "ano": 2015}


async def _inserir_usuario(conexao, perfil: PerfilUsuario) -> Usuario:
    """Usuário gravado no banco: a OS guarda atendente e mecânico com chave estrangeira."""
    usuario = Usuario(
        nome=perfil.value.title(),
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


async def _abrir(cliente_http, cabecalho, documento: str, placa: str, nome: str) -> dict:
    dados = {
        "documento": documento,
        "placa": placa,
        "cliente": {"nome": nome, "email": "c@exemplo.com", "telefone": "11987654321"},
        "veiculo": VEICULO,
    }
    resposta = await cliente_http.post("/ordens-servico", json=dados, headers=cabecalho)
    assert resposta.status_code == 201
    return resposta.json()


async def _atribuir_mecanico(fabrica_de_sessoes, os_id: str, mecanico: Usuario) -> None:
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)
        os = await ordens.buscar_por_id(os_id)
        os.atribuir_mecanico(mecanico.id)
        await ordens.salvar(os)


@pytest.fixture
async def cenario(cliente_http, atendente, conexao, fabrica_de_sessoes):
    """Duas OS: a de Maria, recém-aberta, e a de José, que já tem mecânico (EM_DIAGNOSTICO)."""
    mecanico = await _inserir_usuario(conexao, PerfilUsuario.MECANICO)
    cabecalho = _cabecalho(atendente)
    recebida = await _abrir(cliente_http, cabecalho, CPF_MARIA, "ABC1D23", "Maria")
    em_diagnostico = await _abrir(cliente_http, cabecalho, CPF_JOSE, "DEF2G34", "José")
    await _atribuir_mecanico(fabrica_de_sessoes, UUID(em_diagnostico["id"]), mecanico)
    return {
        "recebida": recebida,
        "em_diagnostico": em_diagnostico,
        "mecanico": mecanico,
    }


async def _listar(cliente_http, atendente, **filtros):
    return await cliente_http.get("/ordens-servico", params=filtros, headers=_cabecalho(atendente))


async def test_lista_as_os_das_mais_recentes_para_as_mais_antigas(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente)

    assert resposta.status_code == 200
    assert [os["numero"] for os in resposta.json()] == [
        cenario["em_diagnostico"]["numero"],
        cenario["recebida"]["numero"],
    ]


async def test_resumo_traz_cliente_placa_mecanico_e_orcamento(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente)
    em_diagnostico, _ = resposta.json()

    assert em_diagnostico == {
        "id": cenario["em_diagnostico"]["id"],
        "numero": cenario["em_diagnostico"]["numero"],
        "status": "EM_DIAGNOSTICO",
        "cliente_nome": "José",
        "placa": "DEF2G34",
        "mecanico_nome": "Mecanico",
        "data_abertura": em_diagnostico["data_abertura"],
        "valor_total": None,
    }


async def test_filtra_por_status(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, status="RECEBIDA")

    assert [os["id"] for os in resposta.json()] == [cenario["recebida"]["id"]]


async def test_filtra_por_mecanico(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, mecanico_id=str(cenario["mecanico"].id))

    assert [os["id"] for os in resposta.json()] == [cenario["em_diagnostico"]["id"]]


async def test_filtra_pelo_documento_do_cliente(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, documento=CPF_MARIA)

    assert [os["id"] for os in resposta.json()] == [cenario["recebida"]["id"]]


async def test_documento_sem_cadastro_devolve_lista_vazia(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, documento=CPF_SEM_CADASTRO)

    assert resposta.status_code == 200
    assert resposta.json() == []


async def test_filtra_pela_placa_em_qualquer_formato(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, placa="def-2g34")

    assert [os["id"] for os in resposta.json()] == [cenario["em_diagnostico"]["id"]]


async def test_filtra_pelo_periodo_de_abertura(cliente_http, atendente, cenario):
    agora = datetime.now(UTC)

    dentro = await _listar(
        cliente_http,
        atendente,
        abertura_de=(agora - timedelta(hours=1)).isoformat(),
        abertura_ate=(agora + timedelta(hours=1)).isoformat(),
    )
    antes = await _listar(
        cliente_http, atendente, abertura_ate=(agora - timedelta(days=1)).isoformat()
    )

    assert len(dentro.json()) == 2
    assert antes.json() == []


async def test_a_placa_de_veiculo_excluido_continua_listando_as_os_dele(
    cliente_http, atendente, cenario
):
    jose = cenario["em_diagnostico"]
    excluido = await cliente_http.delete(
        f"/veiculos/{jose['veiculo_id']}", headers=_cabecalho(atendente)
    )

    resposta = await _listar(cliente_http, atendente, placa="DEF2G34")

    assert excluido.status_code == 204
    assert [os["id"] for os in resposta.json()] == [jose["id"]]


async def test_placa_reaproveitada_lista_as_os_do_veiculo_antigo_e_do_novo(
    cliente_http, atendente, cenario
):
    cabecalho = _cabecalho(atendente)
    jose = cenario["em_diagnostico"]
    await cliente_http.delete(f"/veiculos/{jose['veiculo_id']}", headers=cabecalho)
    nova = await _abrir(cliente_http, cabecalho, CPF_MARIA, "DEF2G34", "Maria")

    resposta = await _listar(cliente_http, atendente, placa="DEF2G34")

    assert {os["id"] for os in resposta.json()} == {jose["id"], nova["id"]}


async def test_combina_os_filtros(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, documento=CPF_JOSE, status="RECEBIDA")

    assert resposta.json() == []


async def test_periodo_sem_fuso_horario_responde_400(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, abertura_de="2026-10-01T10:00:00")

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_status_inexistente_responde_422(cliente_http, atendente, cenario):
    resposta = await _listar(cliente_http, atendente, status="INVENTADO")

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"


async def test_sem_token_responde_401(cliente_http):
    resposta = await cliente_http.get("/ordens-servico")

    assert resposta.status_code == 401


@pytest.mark.parametrize(
    "perfil", [PerfilUsuario.ATENDENTE, PerfilUsuario.MECANICO, PerfilUsuario.GERENTE]
)
async def test_todos_os_perfis_consultam_a_listagem(cliente_http, conexao, cenario, perfil):
    usuario = await _inserir_usuario(conexao, perfil)

    resposta = await cliente_http.get("/ordens-servico", headers=_cabecalho(usuario))

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2
