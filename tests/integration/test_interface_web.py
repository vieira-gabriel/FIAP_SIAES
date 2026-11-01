"""Entrega das páginas da interface web e cabeçalhos de segurança delas (RNF-04)."""

import pytest

from presentation.middlewares.interface_web import CABECALHOS_DE_SEGURANCA

PAGINAS = ["/oficina/", "/cliente/"]
ARQUIVOS_DAS_PAGINAS = [
    "/comum/api.js",
    "/comum/dom.js",
    "/comum/estilo.css",
    "/oficina/oficina.js",
    "/oficina/detalhe_os.js",
    "/cliente/cliente.js",
]


@pytest.mark.parametrize("caminho", PAGINAS)
async def test_paginas_sao_publicas_e_em_html(cliente_http, caminho):
    resposta = await cliente_http.get(caminho)

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")
    assert '<script type="module"' in resposta.text


@pytest.mark.parametrize("caminho", PAGINAS + ARQUIVOS_DAS_PAGINAS)
async def test_paginas_e_arquivos_levam_os_cabecalhos_de_seguranca(cliente_http, caminho):
    resposta = await cliente_http.get(caminho)

    assert resposta.status_code == 200
    for nome, valor in CABECALHOS_DE_SEGURANCA.items():
        assert resposta.headers[nome] == valor


async def test_revalidacao_sem_mudanca_responde_304_com_os_cabecalhos(cliente_http):
    etag = (await cliente_http.get("/comum/api.js")).headers["etag"]

    resposta = await cliente_http.get("/comum/api.js", headers={"If-None-Match": etag})

    assert resposta.status_code == 304
    assert (
        resposta.headers["content-security-policy"]
        == (CABECALHOS_DE_SEGURANCA["Content-Security-Policy"])
    )


async def test_csp_recusa_script_embutido_e_de_outra_origem(cliente_http):
    politica = (await cliente_http.get("/oficina/")).headers["content-security-policy"]

    assert "script-src 'self';" in politica
    assert "unsafe-inline" not in politica
    assert "frame-ancestors 'none'" in politica


async def test_raiz_leva_a_oficina(cliente_http):
    resposta = await cliente_http.get("/")

    assert resposta.status_code in (302, 307)
    assert resposta.headers["location"] == "/oficina/"


@pytest.mark.parametrize("caminho", ["/docs", "/health", "/clientes"])
async def test_swagger_e_api_ficam_sem_o_csp_das_paginas(cliente_http, caminho):
    resposta = await cliente_http.get(caminho)

    assert "content-security-policy" not in resposta.headers


async def test_arquivo_inexistente_responde_404_no_formato_da_api(cliente_http):
    resposta = await cliente_http.get("/oficina/nao-existe.js")

    assert resposta.status_code == 404
    assert resposta.json()["codigo"]


async def test_interface_nao_aparece_no_openapi(cliente_http):
    caminhos = (await cliente_http.get("/openapi.json")).json()["paths"]

    da_interface = [c for c in caminhos if c.startswith(("/oficina", "/cliente/", "/comum"))]
    assert da_interface == []
    assert "/" not in caminhos
