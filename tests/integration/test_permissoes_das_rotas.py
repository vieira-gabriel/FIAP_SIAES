"""Matriz perfis × rotas da Fase 4 com o guard de RBAC real (RF-01, RF-02, RNF-03, RNF-13).

As permissões vêm dos RF-03 a RF-12. Uma rota nova precisa entrar em `ROTAS`, ou em
`ROTAS_PUBLICAS` se for pública, senão `test_toda_rota_da_aplicacao_esta_na_matriz` falha.
"""

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.security.jwt_token_service import JwtTokenService
from presentation.main import app

ATENDENTE = PerfilUsuario.ATENDENTE
MECANICO = PerfilUsuario.MECANICO
GERENTE = PerfilUsuario.GERENTE
TODOS = frozenset(PerfilUsuario)

ROTAS: list[tuple[str, str, frozenset[PerfilUsuario]]] = [
    ("POST", "/usuarios", frozenset({GERENTE})),
    ("GET", "/usuarios", frozenset({GERENTE})),
    ("GET", "/usuarios/{id}", frozenset({GERENTE})),
    ("PUT", "/usuarios/{id}", frozenset({GERENTE})),
    ("PUT", "/usuarios/{id}/senha", frozenset({GERENTE})),
    ("POST", "/usuarios/{id}/desativar", frozenset({GERENTE})),
    ("POST", "/usuarios/{id}/reativar", frozenset({GERENTE})),
    ("POST", "/clientes", frozenset({ATENDENTE, GERENTE})),
    ("GET", "/clientes", TODOS),
    ("GET", "/clientes/{id}", TODOS),
    ("PUT", "/clientes/{id}", frozenset({ATENDENTE, GERENTE})),
    ("DELETE", "/clientes/{id}", frozenset({GERENTE})),
    ("POST", "/veiculos", frozenset({ATENDENTE, GERENTE})),
    ("GET", "/veiculos", TODOS),
    ("GET", "/veiculos/{id}", TODOS),
    ("PUT", "/veiculos/{id}", frozenset({ATENDENTE, GERENTE})),
    ("DELETE", "/veiculos/{id}", frozenset({ATENDENTE, GERENTE})),
    ("POST", "/servicos", frozenset({GERENTE})),
    ("GET", "/servicos", TODOS),
    ("GET", "/servicos/{id}", TODOS),
    ("PUT", "/servicos/{id}", frozenset({GERENTE})),
    ("DELETE", "/servicos/{id}", frozenset({GERENTE})),
    ("POST", "/pecas", frozenset({GERENTE})),
    ("GET", "/pecas", TODOS),
    ("GET", "/pecas/{id}", TODOS),
    ("PUT", "/pecas/{id}", frozenset({GERENTE})),
    ("DELETE", "/pecas/{id}", frozenset({GERENTE})),
    ("POST", "/pecas/{id}/reposicao", frozenset({MECANICO, GERENTE})),
    ("POST", "/ordens-servico", frozenset({ATENDENTE, GERENTE})),
    ("GET", "/ordens-servico", TODOS),
    ("GET", "/ordens-servico/{id}", TODOS),
    ("POST", "/ordens-servico/{id}/mecanico", frozenset({MECANICO, GERENTE})),
    ("POST", "/ordens-servico/{id}/servicos", frozenset({MECANICO, GERENTE})),
    ("DELETE", "/ordens-servico/{id}/servicos/{servico_id}", frozenset({MECANICO, GERENTE})),
    ("POST", "/ordens-servico/{id}/pecas", frozenset({MECANICO, GERENTE})),
    ("DELETE", "/ordens-servico/{id}/pecas/{peca_id}", frozenset({MECANICO, GERENTE})),
    ("POST", "/ordens-servico/{id}/orcamento", frozenset({MECANICO, GERENTE})),
    ("POST", "/ordens-servico/{id}/cancelamento", frozenset({GERENTE})),
    ("POST", "/ordens-servico/{id}/execucao", frozenset({MECANICO, GERENTE})),
    ("POST", "/ordens-servico/{id}/conclusao", frozenset({MECANICO, GERENTE})),
    ("PUT", "/pecas/{id}/quantidade-fisica", frozenset({MECANICO, GERENTE})),
]

ROTAS_PUBLICAS = {
    ("POST", "/auth/login"),
    ("GET", "/health"),
    ("POST", "/acompanhamento"),
    ("POST", "/acompanhamento/aprovacao"),
}

AUTORIZADOS = [
    pytest.param(metodo, caminho, perfil, id=f"{perfil} {metodo} {caminho}")
    for metodo, caminho, perfis in ROTAS
    for perfil in sorted(perfis)
]
SEM_PERMISSAO = [
    pytest.param(metodo, caminho, perfil, id=f"{perfil} {metodo} {caminho}")
    for metodo, caminho, perfis in ROTAS
    for perfil in sorted(TODOS - perfis)
]
TODAS_AS_ROTAS = [
    pytest.param(metodo, caminho, id=f"{metodo} {caminho}") for metodo, caminho, _ in ROTAS
]


@pytest.fixture
def token_expirado(configuracao) -> dict[str, str]:
    """Mesma chave e mesmas claims da aplicação; o token só é recusado pela expiração."""
    servico = JwtTokenService(
        configuracao.jwt_secret_key.get_secret_value(),
        expiracao_horas=24,
        relogio=lambda: datetime.now(UTC) - timedelta(hours=25),
    )
    usuario = Usuario(nome="Gerente", email="g@oficina.com", senha_hash="h", perfil=GERENTE)
    return {"Authorization": f"Bearer {servico.emitir(usuario)}"}


@pytest.fixture
def token_malformado() -> dict[str, str]:
    return {"Authorization": "Bearer isto-nao-e-um-jwt"}


@pytest.fixture
def sem_token() -> dict[str, str]:
    return {}


async def _requisitar(cliente_http, metodo, caminho, cabecalho):
    """O corpo vazio e o id inexistente bastam: o guard responde antes da validação e do banco."""
    corpo = {} if metodo in {"POST", "PUT"} else None
    return await cliente_http.request(
        metodo, re.sub(r"\{\w+\}", lambda _: str(uuid4()), caminho), json=corpo, headers=cabecalho
    )


@pytest.mark.parametrize(("metodo", "caminho", "perfil"), AUTORIZADOS)
async def test_perfil_autorizado_passa_pelo_guard(cliente_http, metodo, caminho, perfil, request):
    cabecalho = request.getfixturevalue(perfil.lower())

    resposta = await _requisitar(cliente_http, metodo, caminho, cabecalho)

    assert resposta.status_code not in {401, 403}


@pytest.mark.parametrize(("metodo", "caminho", "perfil"), SEM_PERMISSAO)
async def test_perfil_sem_permissao_responde_403(cliente_http, metodo, caminho, perfil, request):
    cabecalho = request.getfixturevalue(perfil.lower())

    resposta = await _requisitar(cliente_http, metodo, caminho, cabecalho)

    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "SEM_PERMISSAO")


@pytest.mark.parametrize("token", ["sem_token", "token_malformado", "token_expirado"])
@pytest.mark.parametrize(("metodo", "caminho"), TODAS_AS_ROTAS)
async def test_token_ausente_ou_invalido_responde_401(
    cliente_http, metodo, caminho, token, request
):
    cabecalho = request.getfixturevalue(token)

    resposta = await _requisitar(cliente_http, metodo, caminho, cabecalho)

    assert (resposta.status_code, resposta.json()["codigo"]) == (401, "NAO_AUTENTICADO")


def test_toda_rota_da_aplicacao_esta_na_matriz():
    """Lê as rotas do OpenAPI porque, no FastAPI 0.143, `app.routes` guarda cada router incluído
    num objeto interno, sem expor as rotas dele. Rota com `include_in_schema=False` escaparia."""
    rotas_da_aplicacao = {
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        for metodo in operacoes
    }

    assert rotas_da_aplicacao == ROTAS_PUBLICAS | {(m, c) for m, c, _ in ROTAS}
