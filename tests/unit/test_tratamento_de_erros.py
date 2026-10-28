import logging
from uuid import uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from application.ports.token_service import TokenInvalido, TokenService, UsuarioAutenticado
from domain.exceptions import (
    AcessoNegado,
    CPFInvalido,
    CredenciaisInvalidas,
    EntidadeNaoEncontrada,
    MotivoObrigatorio,
    PlacaInvalida,
)
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.container import obter_token_service
from presentation.main import app as aplicacao
from presentation.middlewares.dependencies import exigir_perfis
from presentation.middlewares.tratamento_de_erros import registrar_tratamento_de_erros

MENSAGEM_INTERNA = "senha do banco: segredo-que-nao-pode-vazar"


class TokenServiceFalso(TokenService):
    def emitir(self, usuario):
        raise NotImplementedError

    def validar(self, token):
        if token == "mecanico":
            return UsuarioAutenticado(usuario_id=uuid4(), perfil=PerfilUsuario.MECANICO)
        raise TokenInvalido(token)


class Credenciais(BaseModel):
    email: str
    senha: str


def _app_de_teste() -> FastAPI:
    app = FastAPI()
    registrar_tratamento_de_erros(app)
    app.dependency_overrides[obter_token_service] = TokenServiceFalso

    @app.get("/valor-invalido")
    async def valor_invalido():
        raise CPFInvalido()

    @app.get("/placa-invalida")
    async def placa_invalida():
        raise PlacaInvalida("ABC-12")

    @app.get("/nao-encontrada")
    async def nao_encontrada():
        raise EntidadeNaoEncontrada("Ordem de serviço", "123-7F3A9C2B")

    @app.get("/regra-violada")
    async def regra_violada():
        raise MotivoObrigatorio()

    @app.get("/credenciais-invalidas")
    async def credenciais_invalidas():
        raise CredenciaisInvalidas()

    @app.get("/acesso-negado")
    async def acesso_negado():
        raise AcessoNegado("Apenas o mecânico atribuído ou o Gerente pode iniciar a execução.")

    @app.get("/somente-gerente", dependencies=[Depends(exigir_perfis(PerfilUsuario.GERENTE))])
    async def somente_gerente():
        return {}

    @app.post("/entrada")
    async def entrada(dados: Credenciais):
        return {}

    @app.get("/erro-inesperado")
    async def erro_inesperado():
        raise RuntimeError(MENSAGEM_INTERNA)

    return app


@pytest.fixture
async def cliente():
    # Sem `raise_app_exceptions`, o httpx relançaria o erro 500 em vez de devolver a resposta.
    transporte = httpx.ASGITransport(app=_app_de_teste(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        yield cliente


@pytest.mark.parametrize(
    ("rota", "codigo_http", "codigo", "mensagem"),
    [
        ("/valor-invalido", 400, "VALOR_INVALIDO", "CPF inválido."),
        (
            "/placa-invalida",
            400,
            "VALOR_INVALIDO",
            "Placa inválida: 'ABC-12'. Use o padrão antigo (ABC1234) ou Mercosul (ABC1D23).",
        ),
        (
            "/nao-encontrada",
            404,
            "ENTIDADE_NAO_ENCONTRADA",
            "Ordem de serviço não encontrado(a): 123-7F3A9C2B.",
        ),
        ("/regra-violada", 422, "REGRA_DE_NEGOCIO_VIOLADA", "Informe o motivo do cancelamento."),
        ("/credenciais-invalidas", 401, "NAO_AUTENTICADO", "E-mail ou senha inválidos."),
        (
            "/acesso-negado",
            403,
            "SEM_PERMISSAO",
            "Apenas o mecânico atribuído ou o Gerente pode iniciar a execução.",
        ),
    ],
)
async def test_excecao_do_dominio_vira_o_codigo_http_da_tabela(
    cliente, rota, codigo_http, codigo, mensagem
):
    resposta = await cliente.get(rota)

    assert resposta.status_code == codigo_http
    assert resposta.json() == {"codigo": codigo, "mensagem": mensagem, "detalhes": []}


async def test_sem_token_responde_401_no_formato_unico_com_www_authenticate(cliente):
    resposta = await cliente.get("/somente-gerente")

    assert resposta.status_code == 401
    assert resposta.json() == {
        "codigo": "NAO_AUTENTICADO",
        "mensagem": "Token de acesso ausente.",
        "detalhes": [],
    }
    assert resposta.headers["WWW-Authenticate"] == "Bearer"


async def test_token_invalido_responde_401(cliente):
    resposta = await cliente.get(
        "/somente-gerente", headers={"Authorization": "Bearer token-adulterado"}
    )

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "NAO_AUTENTICADO"


async def test_perfil_sem_permissao_responde_403(cliente):
    resposta = await cliente.get("/somente-gerente", headers={"Authorization": "Bearer mecanico"})

    assert resposta.status_code == 403
    assert resposta.json() == {
        "codigo": "SEM_PERMISSAO",
        "mensagem": "Perfil sem permissão para esta operação.",
        "detalhes": [],
    }


async def test_dto_invalido_responde_422_com_os_campos_sem_os_valores_recebidos(cliente):
    resposta = await cliente.post("/entrada", json={"senha": "minha-senha-secreta"})

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "ENTRADA_INVALIDA"
    assert corpo["mensagem"] == "Dados de entrada inválidos."
    assert [detalhe["campo"] for detalhe in corpo["detalhes"]] == ["body.email"]
    assert "minha-senha-secreta" not in resposta.text


async def test_erro_nao_tratado_responde_500_sem_mensagem_interna_nem_stack_trace(cliente, caplog):
    with caplog.at_level(logging.ERROR):
        resposta = await cliente.get("/erro-inesperado")

    assert resposta.status_code == 500
    assert resposta.json() == {
        "codigo": "ERRO_INTERNO",
        "mensagem": "Erro interno. Tente novamente mais tarde.",
        "detalhes": [],
    }
    assert MENSAGEM_INTERNA not in resposta.text
    assert "Traceback" not in resposta.text
    assert "RuntimeError" not in resposta.text


async def test_erro_nao_tratado_e_registrado_no_log_com_a_causa(cliente, caplog):
    with caplog.at_level(logging.ERROR):
        await cliente.get("/erro-inesperado")

    registro = next(r for r in caplog.records if "Erro não tratado" in r.getMessage())
    assert "GET /erro-inesperado" in registro.getMessage()
    assert isinstance(registro.exc_info[1], RuntimeError)


async def test_aplicacao_principal_usa_o_formato_unico():
    transporte = httpx.ASGITransport(app=aplicacao)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        resposta = await cliente.get("/rota-que-nao-existe")

    assert resposta.status_code == 404
    assert resposta.json() == {"codigo": "NAO_ENCONTRADO", "mensagem": "Not Found", "detalhes": []}
