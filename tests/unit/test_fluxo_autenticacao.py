"""Fluxo de autenticação pela API, com JWT e bcrypt reais e usuários em memória.

Cobre login → token → rota protegida → 401/403 sem depender do PostgreSQL. Quando o
repositório PostgreSQL existir, o mesmo fluxo vira teste de integração (RNF-13).
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from application.ports.token_service import UsuarioAutenticado
from application.use_cases.autenticar_usuario import AutenticarUsuario
from domain.entities.usuario import Usuario
from domain.repositories.usuario_repository import UsuarioRepository
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from infrastructure.security.jwt_token_service import JwtTokenService
from presentation.auth.dependencies import exigir_perfis, obter_usuario_autenticado
from presentation.routers.autenticacao import router as autenticacao_router

CHAVE = "chave-de-teste-com-pelo-menos-32-bytes!!"
SENHA = "senha-de-teste"


class UsuarioRepositoryEmMemoria(UsuarioRepository):
    def __init__(self):
        self.dados = {}

    def salvar(self, usuario):
        self.dados[usuario.id] = usuario

    def buscar_por_id(self, id):
        return self.dados.get(id)

    def buscar_por_email(self, email):
        return next((u for u in self.dados.values() if u.email == email), None)


class Relogio:
    def __init__(self):
        self.agora = datetime.now(UTC)

    def __call__(self):
        return self.agora


@pytest.fixture
def relogio():
    return Relogio()


@pytest.fixture
def usuarios():
    hasher = BcryptPasswordHasher(rounds=4)
    repositorio = UsuarioRepositoryEmMemoria()
    for nome, perfil in [
        ("Gerente", PerfilUsuario.GERENTE),
        ("Atendente", PerfilUsuario.ATENDENTE),
        ("Mecanico", PerfilUsuario.MECANICO),
    ]:
        repositorio.salvar(
            Usuario(
                nome=nome,
                email=f"{nome.lower()}@oficina.com",
                senha_hash=hasher.gerar_hash(SENHA),
                perfil=perfil,
            )
        )
    return repositorio


@pytest.fixture
def cliente(usuarios, relogio):
    tokens = JwtTokenService(CHAVE, expiracao_horas=24, relogio=relogio)
    app = FastAPI()
    app.state.token_service = tokens
    app.state.autenticar_usuario = AutenticarUsuario(usuarios, BcryptPasswordHasher(), tokens)
    app.include_router(autenticacao_router)

    @app.get("/qualquer-perfil")
    def qualquer_perfil(
        usuario: Annotated[UsuarioAutenticado, Depends(obter_usuario_autenticado)],
    ):
        return {"usuario_id": str(usuario.usuario_id), "perfil": usuario.perfil.value}

    @app.get("/so-gerente", dependencies=[Depends(exigir_perfis(PerfilUsuario.GERENTE))])
    def so_gerente():
        return {"ok": True}

    return TestClient(app)


def login(cliente, email, senha=SENHA):
    return cliente.post("/auth/login", json={"email": email, "senha": senha})


def token_de(cliente, email):
    return login(cliente, email).json()["access_token"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_valido_devolve_bearer_token(cliente, usuarios):
    resposta = login(cliente, "gerente@oficina.com")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    claims = jwt.decode(
        corpo["access_token"],
        CHAVE,
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["role"] == "GERENTE"
    assert claims["sub"] == str(usuarios.buscar_por_email("gerente@oficina.com").id)


@pytest.mark.parametrize(
    ("email", "senha"),
    [
        ("gerente@oficina.com", "senha-errada"),
        ("ninguem@oficina.com", SENHA),
    ],
)
def test_login_invalido_retorna_401_com_a_mesma_mensagem(cliente, email, senha):
    resposta = login(cliente, email, senha)

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "E-mail ou senha inválidos."}


def test_login_de_usuario_desativado_retorna_401(cliente, usuarios):
    usuarios.buscar_por_email("atendente@oficina.com").desativar()

    assert login(cliente, "atendente@oficina.com").status_code == 401


def test_login_sem_campos_obrigatorios_retorna_422(cliente):
    assert cliente.post("/auth/login", json={"email": "gerente@oficina.com"}).status_code == 422


def test_token_do_login_acessa_rota_protegida(cliente, usuarios):
    token = token_de(cliente, "mecanico@oficina.com")

    resposta = cliente.get("/qualquer-perfil", headers=bearer(token))

    assert resposta.status_code == 200
    assert resposta.json() == {
        "usuario_id": str(usuarios.buscar_por_email("mecanico@oficina.com").id),
        "perfil": "MECANICO",
    }


@pytest.mark.parametrize(
    ("email", "esperado"),
    [
        ("gerente@oficina.com", 200),
        ("atendente@oficina.com", 403),
        ("mecanico@oficina.com", 403),
    ],
)
def test_rbac_com_token_real(cliente, email, esperado):
    token = token_de(cliente, email)

    assert cliente.get("/so-gerente", headers=bearer(token)).status_code == esperado


def test_rota_protegida_sem_token_retorna_401(cliente):
    assert cliente.get("/qualquer-perfil").status_code == 401
    assert cliente.get("/so-gerente").status_code == 401


def test_token_adulterado_retorna_401(cliente):
    token = token_de(cliente, "atendente@oficina.com")
    cabecalho, payload, assinatura = token.split(".")
    adulterado = f"{cabecalho}.{payload}.{assinatura[:-2]}xx"

    assert cliente.get("/qualquer-perfil", headers=bearer(adulterado)).status_code == 401


def test_token_forjado_com_outra_chave_retorna_401(cliente):
    agora = datetime.now(UTC)
    forjado = jwt.encode(
        {"sub": "x", "role": "GERENTE", "iat": agora, "exp": agora + timedelta(hours=1)},
        "chave-do-atacante-com-pelo-menos-32-bytes",
        algorithm="HS256",
    )

    assert cliente.get("/so-gerente", headers=bearer(forjado)).status_code == 401


def test_token_expira_depois_de_24_horas(cliente, relogio):
    token = token_de(cliente, "gerente@oficina.com")

    relogio.agora += timedelta(hours=23, minutes=59)
    assert cliente.get("/so-gerente", headers=bearer(token)).status_code == 200

    relogio.agora += timedelta(minutes=1)
    assert cliente.get("/so-gerente", headers=bearer(token)).status_code == 401
