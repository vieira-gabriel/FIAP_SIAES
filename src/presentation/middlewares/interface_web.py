"""Entrega das páginas da interface web e cabeçalhos de segurança delas.

As páginas são arquivos estáticos que chamam a própria API pelo navegador, na mesma origem, então
não há CORS. A Frente da Loja fica em `/oficina/` e a Frente do Cliente em `/cliente/`.

O CSP vale só para as páginas: o Swagger em `/docs` carrega scripts de CDN e scripts embutidos,
que a política das páginas recusaria. Sem `'unsafe-inline'`, um texto vindo da API que chegasse
ao HTML como marcação não executa script (RNF-04).
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

_PASTA_WEB = Path(__file__).resolve().parent.parent / "web"
_PREFIXOS = ("/oficina", "/cliente", "/comum")

CABECALHOS_DE_SEGURANCA = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    # Sem isso o navegador reaproveita um módulo JS antigo depois de uma atualização; com ele,
    # confere a versão a cada carga e recebe 304 quando nada mudou.
    "Cache-Control": "no-cache",
}


def registrar_interface_web(app: FastAPI) -> None:
    app.mount("/comum", StaticFiles(directory=_PASTA_WEB / "comum"), name="comum")
    app.mount("/oficina", StaticFiles(directory=_PASTA_WEB / "oficina", html=True), name="oficina")
    app.mount("/cliente", StaticFiles(directory=_PASTA_WEB / "cliente", html=True), name="cliente")
    app.add_api_route("/", _ir_para_a_oficina, include_in_schema=False)
    app.middleware("http")(_aplicar_cabecalhos_de_seguranca)


async def _ir_para_a_oficina() -> RedirectResponse:
    return RedirectResponse("/oficina/")


async def _aplicar_cabecalhos_de_seguranca(
    request: Request, proximo: Callable[[Request], Awaitable[Response]]
) -> Response:
    resposta = await proximo(request)
    if _e_da_interface(request.url.path):
        resposta.headers.update(CABECALHOS_DE_SEGURANCA)
    return resposta


def _e_da_interface(caminho: str) -> bool:
    # Compara o segmento inteiro: "/cliente" não pode valer para a rota da API "/clientes".
    return any(caminho == prefixo or caminho.startswith(f"{prefixo}/") for prefixo in _PREFIXOS)
