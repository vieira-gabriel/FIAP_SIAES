"""Login pela aplicação completa, com PostgreSQL, migrations e carga inicial reais.

Cobre RF-01 e RF-03 como teste de integração (RNF-13).
"""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from presentation.main import app

SENHA_ADMIN = "senha-do-admin-de-teste"
SENHA_ATENDENTE = "senha-do-atendente-de-teste"
SENHA_MECANICO = "senha-do-mecanico-de-teste"


@pytest.fixture
def ambiente(banco_migrado, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", SENHA_ADMIN)
    monkeypatch.setenv("SEED_DEMO", "true")
    monkeypatch.setenv("DEMO_ATENDENTE_PASSWORD", SENHA_ATENDENTE)
    monkeypatch.setenv("DEMO_MECANICO_PASSWORD", SENHA_MECANICO)
    return banco_migrado


@pytest.fixture
def cliente(ambiente):
    with TestClient(app) as cliente:
        yield cliente


def _login(cliente, email, senha):
    return cliente.post("/auth/login", json={"email": email, "senha": senha})


async def _contar_usuarios(engine) -> int:
    async with engine.connect() as conexao:
        return (await conexao.execute(text("SELECT count(*) FROM usuarios"))).scalar_one()


@pytest.mark.parametrize(
    ("email", "senha", "perfil"),
    [
        ("admin@oficina.com", SENHA_ADMIN, "GERENTE"),
        ("atendente@oficina.com", SENHA_ATENDENTE, "ATENDENTE"),
        ("mecanico@oficina.com", SENHA_MECANICO, "MECANICO"),
    ],
)
def test_usuarios_da_carga_inicial_fazem_login(cliente, email, senha, perfil):
    resposta = _login(cliente, email, senha)

    assert resposta.status_code == 200
    token = resposta.json()["access_token"]
    assert jwt.decode(token, options={"verify_signature": False})["role"] == perfil


def test_senha_errada_retorna_401(cliente):
    assert _login(cliente, "admin@oficina.com", "senha-errada").status_code == 401


def test_email_inexistente_retorna_401(cliente):
    assert _login(cliente, "ninguem@oficina.com", SENHA_ADMIN).status_code == 401


async def test_reiniciar_a_aplicacao_nao_duplica_nem_troca_a_senha(ambiente, monkeypatch):
    with TestClient(app):
        pass
    monkeypatch.setenv("ADMIN_PASSWORD", "outra-senha-na-segunda-subida")

    with TestClient(app) as cliente:
        assert _login(cliente, "admin@oficina.com", SENHA_ADMIN).status_code == 200

    assert await _contar_usuarios(ambiente) == 3
