"""Entrega das páginas da interface web e cabeçalhos de segurança delas.

As páginas são arquivos estáticos que chamam a própria API pelo navegador, na mesma origem, então
não há CORS. A Frente da Loja fica em `/oficina/` e a Frente do Cliente em `/cliente/`.

O CSP vale só para as páginas: o Swagger em `/docs` carrega scripts de CDN e scripts embutidos,
que a política das páginas recusaria. Sem `'unsafe-inline'`, um texto vindo da API que chegasse
ao HTML como marcação não executa script (RNF-04).
"""

import os
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

_PASTA_WEB = Path(__file__).resolve().parent.parent / "web"

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


class _ArquivosDaInterface(StaticFiles):
    # Os cabeçalhos entram só nas respostas da interface; um middleware HTTP passaria por todas
    # as rotas da API (RNF-10) para depois descartar quase todas.
    def file_response(
        self,
        full_path: os.PathLike[str] | str,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        resposta = super().file_response(full_path, stat_result, scope, status_code)
        resposta.headers.update(CABECALHOS_DE_SEGURANCA)
        return resposta


def registrar_interface_web(app: FastAPI) -> None:
    app.mount("/comum", _ArquivosDaInterface(directory=_PASTA_WEB / "comum"), name="comum")
    for frente in ("oficina", "cliente"):
        pasta = _PASTA_WEB / frente
        app.mount(f"/{frente}", _ArquivosDaInterface(directory=pasta, html=True), name=frente)
    app.add_api_route("/", _ir_para_a_oficina, include_in_schema=False)


async def _ir_para_a_oficina() -> RedirectResponse:
    return RedirectResponse("/oficina/")
