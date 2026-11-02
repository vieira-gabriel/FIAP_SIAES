"""Aprovação e rejeição do orçamento registradas no balcão, pelas rotas HTTP e com PostgreSQL real
(RNF-13, RF-18, RF-24, RF-26)."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

ABERTURA = {
    "documento": "529.982.247-25",
    "placa": "ABC1D23",
    "cliente": {"nome": "Maria Silva", "email": "maria@exemplo.com", "telefone": "11987654321"},
    "veiculo": {"marca": "Fiat", "modelo": "Uno", "ano": 2015},
}
PECA = {
    "codigo_referencia": "FLT-001",
    "nome": "Filtro de óleo",
    "preco_unitario": "35.90",
    "prazo_reposicao_dias": 3,
    "quantidade_fisica_inicial": 5,
}


async def _inserir_usuario(conexao, perfil: PerfilUsuario) -> Usuario:
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


@pytest.fixture
async def mecanico(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.MECANICO)


@pytest.fixture
async def gerente(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.GERENTE)


@pytest.fixture
async def os_orcada(cliente_http, atendente, mecanico, gerente) -> dict:
    """OS em `AGUARDANDO_APROVACAO` com duas unidades da peça reservadas."""
    peca = await cliente_http.post("/pecas", json=PECA, headers=_cabecalho(gerente))
    aberta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    os = aberta.json() | {"peca_id": peca.json()["id"]}
    base = f"/ordens-servico/{os['id']}"
    await cliente_http.post(f"{base}/mecanico", headers=_cabecalho(mecanico))
    await cliente_http.post(
        f"{base}/pecas",
        json={"peca_id": os["peca_id"], "quantidade": 2},
        headers=_cabecalho(mecanico),
    )
    resposta = await cliente_http.post(f"{base}/orcamento", headers=_cabecalho(mecanico))
    assert resposta.json()["status"] == "AGUARDANDO_APROVACAO"
    return os


async def _decidir(cliente_http, quem, os_id: str, decisao: str):
    return await cliente_http.post(
        f"/ordens-servico/{os_id}/orcamento/{decisao}", headers=_cabecalho(quem)
    )


async def _ultimo_registro(cliente_http, quem, os_id: str) -> dict:
    detalhe = await cliente_http.get(f"/ordens-servico/{os_id}", headers=_cabecalho(quem))
    return detalhe.json()["historico"][-1]


async def test_atendente_aprova_no_balcao_e_o_historico_registra_o_atendente(
    cliente_http, atendente, os_orcada
):
    resposta = await _decidir(cliente_http, atendente, os_orcada["id"], "aprovacao")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "AGUARDANDO_EXECUCAO"
    registro = await _ultimo_registro(cliente_http, atendente, os_orcada["id"])
    assert (registro["origem"], registro["usuario_id"]) == ("USUARIO", str(atendente.id))


async def test_gerente_rejeita_no_balcao_e_as_reservas_voltam_ao_saldo(
    cliente_http, gerente, os_orcada
):
    resposta = await _decidir(cliente_http, gerente, os_orcada["id"], "rejeicao")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"
    peca = await cliente_http.get(f"/pecas/{os_orcada['peca_id']}", headers=_cabecalho(gerente))
    assert (peca.json()["quantidade_reservada"], peca.json()["saldo_disponivel"]) == (0, 5)
    registro = await _ultimo_registro(cliente_http, gerente, os_orcada["id"])
    assert (registro["origem"], registro["usuario_id"]) == ("USUARIO", str(gerente.id))


@pytest.mark.parametrize("decisao", ["aprovacao", "rejeicao"])
async def test_mecanico_recebe_403(cliente_http, mecanico, os_orcada, decisao):
    resposta = await _decidir(cliente_http, mecanico, os_orcada["id"], decisao)

    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "SEM_PERMISSAO")


@pytest.mark.parametrize("decisao", ["aprovacao", "rejeicao"])
async def test_segunda_decisao_responde_422(cliente_http, atendente, os_orcada, decisao):
    primeira = await _decidir(cliente_http, atendente, os_orcada["id"], "aprovacao")
    segunda = await _decidir(cliente_http, atendente, os_orcada["id"], decisao)

    assert (primeira.status_code, segunda.status_code) == (200, 422)
    assert segunda.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


@pytest.mark.parametrize("decisao", ["aprovacao", "rejeicao"])
async def test_os_inexistente_responde_404(cliente_http, atendente, decisao):
    resposta = await _decidir(cliente_http, atendente, str(uuid4()), decisao)

    assert resposta.status_code == 404
