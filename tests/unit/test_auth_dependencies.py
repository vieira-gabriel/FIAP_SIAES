from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from application.ports.token_service import TokenInvalido, TokenService, UsuarioAutenticado
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.auth.dependencies import exigir_perfis, obter_usuario_autenticado


class TokenServiceFalso(TokenService):
    """Aceita tokens no formato `valido:<PERFIL>`."""

    def emitir(self, usuario):
        raise NotImplementedError

    def validar(self, token):
        prefixo, _, perfil = token.partition(":")
        if prefixo != "valido":
            raise TokenInvalido("token inválido")
        return UsuarioAutenticado(uuid4(), PerfilUsuario(perfil))


@pytest.fixture
def cliente():
    app = FastAPI()
    app.state.token_service = TokenServiceFalso()

    @app.get("/protegida")
    def protegida(usuario: Annotated[UsuarioAutenticado, Depends(obter_usuario_autenticado)]):
        return {"perfil": usuario.perfil.value}

    @app.get("/gerencia", dependencies=[Depends(exigir_perfis(PerfilUsuario.GERENTE))])
    def gerencia():
        return {"ok": True}

    somente_oficina = exigir_perfis(PerfilUsuario.MECANICO, PerfilUsuario.GERENTE)

    @app.get("/oficina")
    def oficina(
        usuario: Annotated[UsuarioAutenticado, Depends(somente_oficina)],
    ):
        return {"perfil": usuario.perfil.value}

    return TestClient(app)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_sem_token_retorna_401(cliente):
    resposta = cliente.get("/protegida")

    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"] == "Bearer"


def test_token_invalido_retorna_401(cliente):
    assert cliente.get("/protegida", headers=bearer("adulterado")).status_code == 401


def test_esquema_diferente_de_bearer_retorna_401(cliente):
    resposta = cliente.get("/protegida", headers={"Authorization": "Basic abc"})

    assert resposta.status_code == 401


def test_token_valido_entrega_o_usuario(cliente):
    resposta = cliente.get("/protegida", headers=bearer("valido:ATENDENTE"))

    assert resposta.status_code == 200
    assert resposta.json() == {"perfil": "ATENDENTE"}


@pytest.mark.parametrize(
    ("rota", "perfil", "esperado"),
    [
        ("/gerencia", "GERENTE", 200),
        ("/gerencia", "MECANICO", 403),
        ("/gerencia", "ATENDENTE", 403),
        ("/oficina", "MECANICO", 200),
        ("/oficina", "GERENTE", 200),
        ("/oficina", "ATENDENTE", 403),
    ],
)
def test_rbac_por_perfil(cliente, rota, perfil, esperado):
    assert cliente.get(rota, headers=bearer(f"valido:{perfil}")).status_code == esperado


def test_rota_com_perfil_exige_token_antes_do_perfil(cliente):
    assert cliente.get("/gerencia").status_code == 401


def test_exigir_perfis_sem_perfis():
    with pytest.raises(ValueError):
        exigir_perfis()
