"""Tradução das exceções em respostas HTTP no formato único `ErroResponse` (guia §5.5, RNF-03)."""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from domain.exceptions import (
    AcessoNegado,
    CredenciaisInvalidas,
    EntidadeNaoEncontrada,
    ErroDeDominio,
    RegraDeNegocioViolada,
    ValorInvalido,
)
from presentation.schemas.erro import DetalheDoErro, ErroResponse

logger = logging.getLogger(__name__)

_ERROS_DE_DOMINIO: list[tuple[type[ErroDeDominio], int, str]] = [
    (ValorInvalido, status.HTTP_400_BAD_REQUEST, "VALOR_INVALIDO"),
    (CredenciaisInvalidas, status.HTTP_401_UNAUTHORIZED, "NAO_AUTENTICADO"),
    (AcessoNegado, status.HTTP_403_FORBIDDEN, "SEM_PERMISSAO"),
    (EntidadeNaoEncontrada, status.HTTP_404_NOT_FOUND, "ENTIDADE_NAO_ENCONTRADA"),
    (RegraDeNegocioViolada, status.HTTP_422_UNPROCESSABLE_CONTENT, "REGRA_DE_NEGOCIO_VIOLADA"),
]

_CODIGOS_POR_STATUS = {
    status.HTTP_401_UNAUTHORIZED: "NAO_AUTENTICADO",
    status.HTTP_403_FORBIDDEN: "SEM_PERMISSAO",
    status.HTTP_404_NOT_FOUND: "NAO_ENCONTRADO",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METODO_NAO_PERMITIDO",
}

_MENSAGEM_DO_ERRO_INTERNO = "Erro interno. Tente novamente mais tarde."


def registrar_tratamento_de_erros(app: FastAPI) -> None:
    for tipo, codigo_http, codigo in _ERROS_DE_DOMINIO:
        app.add_exception_handler(tipo, _tratador_de_erro_de_dominio(codigo_http, codigo))
    app.add_exception_handler(RequestValidationError, _tratar_entrada_invalida)
    app.add_exception_handler(HTTPException, _tratar_http_exception)
    app.add_exception_handler(Exception, _tratar_erro_interno)


def _tratador_de_erro_de_dominio(codigo_http: int, codigo: str):
    async def tratar(_request: Request, erro: ErroDeDominio) -> JSONResponse:
        return _resposta(codigo_http, ErroResponse(codigo=codigo, mensagem=str(erro)))

    return tratar


async def _tratar_entrada_invalida(_request: Request, erro: RequestValidationError) -> JSONResponse:
    """Só o campo e a mensagem de cada erro: o valor recebido poderia ser uma senha."""
    detalhes = [
        DetalheDoErro(campo=".".join(str(parte) for parte in item["loc"]), mensagem=item["msg"])
        for item in erro.errors()
    ]
    corpo = ErroResponse(
        codigo="ENTRADA_INVALIDA",
        mensagem="Dados de entrada inválidos.",
        detalhes=detalhes,
    )
    return _resposta(status.HTTP_422_UNPROCESSABLE_CONTENT, corpo)


async def _tratar_http_exception(_request: Request, erro: HTTPException) -> JSONResponse:
    """Mantém o código e os cabeçalhos da exceção, como o `WWW-Authenticate` do 401."""
    corpo = ErroResponse(
        codigo=_CODIGOS_POR_STATUS.get(erro.status_code, HTTPStatus(erro.status_code).name),
        mensagem=str(erro.detail),
    )
    return _resposta(erro.status_code, corpo, erro.headers)


async def _tratar_erro_interno(request: Request, erro: Exception) -> JSONResponse:
    """A causa vai só para o log; a resposta não expõe mensagem interna nem stack trace."""
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path, exc_info=erro)
    corpo = ErroResponse(codigo="ERRO_INTERNO", mensagem=_MENSAGEM_DO_ERRO_INTERNO)
    return _resposta(status.HTTP_500_INTERNAL_SERVER_ERROR, corpo)


def _resposta(
    codigo_http: int, corpo: ErroResponse, cabecalhos: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(status_code=codigo_http, content=corpo.model_dump(), headers=cabecalhos)
