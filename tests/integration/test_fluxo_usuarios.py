"""Gestão de usuários internos pelo Gerente, pelas rotas HTTP com PostgreSQL (RF-03, RNF-13)."""

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

NOVA_ATENDENTE = {
    "nome": "Bia Atendente",
    "email": "Bia@Oficina.com",
    "senha": "senha-da-bia-123",
    "perfil": "ATENDENTE",
}


@pytest.fixture
async def gerente(cliente_http, configuracao):
    """Login real do Gerente criado pela carga inicial, para o token ter o id dele."""
    resposta = await cliente_http.post(
        "/auth/login",
        json={
            "email": "admin@oficina.com",
            "senha": configuracao.admin_password.get_secret_value(),
        },
    )
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
async def id_do_gerente(cliente_http, gerente):
    usuarios = (await cliente_http.get("/usuarios", headers=gerente)).json()
    return next(u["id"] for u in usuarios if u["email"] == "admin@oficina.com")


def _cabecalho(perfil: PerfilUsuario) -> dict[str, str]:
    usuario = Usuario(nome="Qualquer", email="q@oficina.com", senha_hash="h", perfil=perfil)
    return {"Authorization": f"Bearer {app.state.token_service.emitir(usuario)}"}


async def _cadastrar(cliente_http, gerente, dados=NOVA_ATENDENTE):
    return await cliente_http.post("/usuarios", json=dados, headers=gerente)


async def _login(cliente_http, email, senha):
    return await cliente_http.post("/auth/login", json={"email": email, "senha": senha})


async def test_gerente_cadastra_usuario_sem_expor_a_senha(cliente_http, gerente, conexao):
    resposta = await _cadastrar(cliente_http, gerente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert set(corpo) == {"id", "nome", "email", "perfil", "ativo"}
    assert (corpo["email"], corpo["perfil"], corpo["ativo"]) == (
        "bia@oficina.com",
        "ATENDENTE",
        True,
    )
    senha_hash = await conexao.scalar(
        text("SELECT senha_hash FROM usuarios WHERE email = 'bia@oficina.com'")
    )
    assert senha_hash.startswith("$2b$")
    assert NOVA_ATENDENTE["senha"] not in senha_hash


async def test_usuario_cadastrado_faz_login_com_o_perfil_definido(cliente_http, gerente):
    await _cadastrar(cliente_http, gerente)

    resposta = await _login(cliente_http, "bia@oficina.com", NOVA_ATENDENTE["senha"])

    assert resposta.status_code == 200


async def test_email_ja_cadastrado_responde_422(cliente_http, gerente):
    resposta = await _cadastrar(
        cliente_http, gerente, NOVA_ATENDENTE | {"email": "ADMIN@oficina.com"}
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


@pytest.mark.parametrize("senha", ["curta", "ç" * 37])
async def test_senha_curta_ou_acima_de_72_bytes_responde_422(cliente_http, gerente, senha):
    resposta = await _cadastrar(cliente_http, gerente, NOVA_ATENDENTE | {"senha": senha})

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"
    assert senha not in resposta.text


async def test_email_invalido_responde_400(cliente_http, gerente):
    resposta = await _cadastrar(cliente_http, gerente, NOVA_ATENDENTE | {"email": "sem-arroba"})

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_desativado_nao_faz_login_e_reativado_volta_a_fazer(cliente_http, gerente):
    bia = (await _cadastrar(cliente_http, gerente)).json()
    senha = NOVA_ATENDENTE["senha"]

    desativacao = await cliente_http.post(f"/usuarios/{bia['id']}/desativar", headers=gerente)
    login_desativado = await _login(cliente_http, "bia@oficina.com", senha)
    reativacao = await cliente_http.post(f"/usuarios/{bia['id']}/reativar", headers=gerente)
    login_reativado = await _login(cliente_http, "bia@oficina.com", senha)

    assert desativacao.status_code == 204
    assert login_desativado.status_code == 401
    assert reativacao.status_code == 204
    assert login_reativado.status_code == 200


async def test_listagem_mostra_o_usuario_desativado(cliente_http, gerente):
    bia = (await _cadastrar(cliente_http, gerente)).json()
    await cliente_http.post(f"/usuarios/{bia['id']}/desativar", headers=gerente)

    lista = (await cliente_http.get("/usuarios", headers=gerente)).json()

    assert {"email": "bia@oficina.com", "ativo": False}.items() <= next(
        u for u in lista if u["id"] == bia["id"]
    ).items()


async def test_atualiza_dados_e_perfil(cliente_http, gerente):
    bia = (await _cadastrar(cliente_http, gerente)).json()

    resposta = await cliente_http.put(
        f"/usuarios/{bia['id']}",
        json={"nome": "Bia Mecânica", "email": "bia@oficina.com", "perfil": "MECANICO"},
        headers=gerente,
    )

    assert resposta.status_code == 200
    assert (resposta.json()["nome"], resposta.json()["perfil"]) == ("Bia Mecânica", "MECANICO")


async def test_troca_de_senha_pelo_gerente(cliente_http, gerente):
    bia = (await _cadastrar(cliente_http, gerente)).json()

    troca = await cliente_http.put(
        f"/usuarios/{bia['id']}/senha", json={"senha": "nova-senha-da-bia"}, headers=gerente
    )

    assert troca.status_code == 204
    assert (
        await _login(cliente_http, "bia@oficina.com", NOVA_ATENDENTE["senha"])
    ).status_code == 401
    assert (await _login(cliente_http, "bia@oficina.com", "nova-senha-da-bia")).status_code == 200


async def test_gerente_nao_desativa_a_si_mesmo(cliente_http, gerente, id_do_gerente):
    resposta = await cliente_http.post(f"/usuarios/{id_do_gerente}/desativar", headers=gerente)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_gerente_nao_muda_o_proprio_perfil(cliente_http, gerente, id_do_gerente):
    resposta = await cliente_http.put(
        f"/usuarios/{id_do_gerente}",
        json={"nome": "Administrador", "email": "admin@oficina.com", "perfil": "ATENDENTE"},
        headers=gerente,
    )

    assert resposta.status_code == 422


async def test_usuario_inexistente_responde_404(cliente_http, gerente):
    resposta = await cliente_http.get(
        "/usuarios/00000000-0000-4000-8000-000000000000", headers=gerente
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


@pytest.mark.parametrize("perfil", [PerfilUsuario.ATENDENTE, PerfilUsuario.MECANICO])
async def test_so_o_gerente_acessa_a_gestao_de_usuarios(cliente_http, perfil):
    cabecalho = _cabecalho(perfil)

    assert (await cliente_http.get("/usuarios", headers=cabecalho)).status_code == 403
    assert (
        await cliente_http.post("/usuarios", json=NOVA_ATENDENTE, headers=cabecalho)
    ).status_code == 403


async def test_sem_token_responde_401(cliente_http):
    assert (await cliente_http.get("/usuarios")).status_code == 401
