from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from application.ports.token_service import TokenInvalido
from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.security.jwt_token_service import JwtTokenService

CHAVE = "chave-de-teste-com-pelo-menos-32-bytes!!"
INICIO = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


class Relogio:
    def __init__(self, agora: datetime):
        self.agora = agora

    def __call__(self) -> datetime:
        return self.agora


@pytest.fixture
def relogio():
    return Relogio(INICIO)


@pytest.fixture
def servico(relogio):
    return JwtTokenService(CHAVE, expiracao_horas=24, relogio=relogio)


@pytest.fixture
def mecanico():
    return Usuario(
        nome="Mecânico",
        email="mecanico@oficina.com",
        senha_hash="h",
        perfil=PerfilUsuario.MECANICO,
    )


def test_token_emitido_e_validado(servico, mecanico):
    autenticado = servico.validar(servico.emitir(mecanico))

    assert autenticado.usuario_id == mecanico.id
    assert autenticado.perfil == PerfilUsuario.MECANICO


def test_token_tem_claim_role_e_expira_em_24_horas(servico, mecanico):
    claims = jwt.decode(
        servico.emitir(mecanico),
        CHAVE,
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    assert claims["role"] == "MECANICO"
    assert claims["sub"] == str(mecanico.id)
    assert claims["exp"] - claims["iat"] == 24 * 3600


def test_token_expirado(servico, relogio, mecanico):
    token = servico.emitir(mecanico)

    relogio.agora = INICIO + timedelta(hours=24) - timedelta(seconds=1)
    assert servico.validar(token)

    relogio.agora = INICIO + timedelta(hours=24)
    with pytest.raises(TokenInvalido):
        servico.validar(token)


def test_token_assinado_com_outra_chave(servico, mecanico, relogio):
    outro = JwtTokenService("outra-chave-com-pelo-menos-32-bytes!!!!", relogio=relogio)

    with pytest.raises(TokenInvalido):
        servico.validar(outro.emitir(mecanico))


def test_token_malformado(servico):
    with pytest.raises(TokenInvalido):
        servico.validar("nao.e.um-jwt")


def test_token_sem_assinatura_e_recusado(servico):
    claims = {
        "sub": str(uuid4()),
        "role": "GERENTE",
        "iat": INICIO,
        "exp": INICIO + timedelta(hours=1),
    }
    token = jwt.encode(claims, None, algorithm="none")

    with pytest.raises(TokenInvalido):
        servico.validar(token)


@pytest.mark.parametrize(
    "claims",
    [
        {"sub": str(uuid4()), "role": "DONO"},
        {"sub": "nao-e-uuid", "role": "GERENTE"},
        {"role": "GERENTE"},
        {"sub": str(uuid4())},
    ],
)
def test_token_com_claims_invalidas(servico, claims):
    claims = {**claims, "iat": INICIO, "exp": INICIO + timedelta(hours=1)}
    token = jwt.encode(claims, CHAVE, algorithm="HS256")

    with pytest.raises(TokenInvalido):
        servico.validar(token)


@pytest.mark.parametrize(("chave", "horas"), [("", 24), (CHAVE, 0)])
def test_configuracao_invalida(chave, horas):
    with pytest.raises(ValueError):
        JwtTokenService(chave, expiracao_horas=horas)
