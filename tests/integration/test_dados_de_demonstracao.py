"""Dados de demonstração gravados pela subida da aplicação, com PostgreSQL e migrations reais.

Com `SEED_DEMO=true`, a carga inicial cria o catálogo, os clientes e uma OS em cada status
(RF-03, RF-13, RNF-13).
"""

import pytest
from fastapi.testclient import TestClient

from domain.value_objects.status_os import StatusOS
from presentation.main import app

SENHA_ADMIN = "senha-do-admin-de-teste"


@pytest.fixture
def ambiente(banco_migrado, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", SENHA_ADMIN)
    monkeypatch.setenv("SEED_DEMO", "true")
    monkeypatch.setenv("DEMO_ATENDENTE_PASSWORD", "senha-do-atendente-de-teste")
    monkeypatch.setenv("DEMO_MECANICO_PASSWORD", "senha-do-mecanico-de-teste")
    return banco_migrado


def _cabecalho_do_gerente(cliente) -> dict[str, str]:
    resposta = cliente.post(
        "/auth/login", json={"email": "admin@oficina.com", "senha": SENHA_ADMIN}
    )
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def _ler(cliente, caminho) -> list[dict]:
    resposta = cliente.get(caminho, headers=_cabecalho_do_gerente(cliente))
    assert resposta.status_code == 200
    return resposta.json()


def test_subida_cria_catalogo_e_uma_os_em_cada_status(ambiente):
    with TestClient(app) as cliente:
        ordens = _ler(cliente, "/ordens-servico")
        assert len(_ler(cliente, "/servicos")) == 5
        assert len(_ler(cliente, "/pecas")) == 3
        assert {os["status"] for os in ordens} == {status.value for status in StatusOS}


def test_detalhe_de_cada_os_de_demonstracao(ambiente):
    with TestClient(app) as cliente:
        cabecalho = _cabecalho_do_gerente(cliente)
        ordens = cliente.get("/ordens-servico", headers=cabecalho).json()
        for os in ordens:
            resposta = cliente.get(f"/ordens-servico/{os['id']}", headers=cabecalho)
            assert resposta.status_code == 200
            assert resposta.json()["historico"][-1]["status_novo"] == os["status"]


def test_reiniciar_a_aplicacao_nao_duplica_os_dados(ambiente):
    with TestClient(app) as cliente:
        antes = len(_ler(cliente, "/ordens-servico")), len(_ler(cliente, "/clientes"))
    with TestClient(app) as cliente:
        depois = len(_ler(cliente, "/ordens-servico")), len(_ler(cliente, "/clientes"))

    assert depois == antes
