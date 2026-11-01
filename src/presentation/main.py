from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from presentation.container import (
    encerrar_dependencias,
    executar_carga_inicial,
    montar_dependencias,
)
from presentation.middlewares.tratamento_de_erros import registrar_tratamento_de_erros
from presentation.routers import (
    acompanhamento_publico,
    autenticacao,
    clientes,
    ordens_servico,
    pecas,
    relatorios,
    saude,
    servicos,
    usuarios,
    veiculos,
)

# Mesma versão do pyproject.toml; o pacote não é instalado na imagem, então não há metadados.
VERSAO_DA_API = "0.1.0"
DESCRICAO_DA_API = (
    "API do Sistema Integrado de Atendimento e Execução de Serviços (SIAES), "
    "para a gestão de ordens de serviço, clientes, veículos e peças da oficina mecânica, "
    "com acompanhamento pelo cliente."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    montar_dependencias(app)
    try:
        await executar_carga_inicial(app)
        yield
    finally:
        await encerrar_dependencias(app)


app = FastAPI(
    title="SIAES - API da Oficina Mecânica",
    version=VERSAO_DA_API,
    description=DESCRICAO_DA_API,
    lifespan=lifespan,
)
registrar_tratamento_de_erros(app)
app.include_router(saude.router)
app.include_router(autenticacao.router)
app.include_router(clientes.router)
app.include_router(usuarios.router)
app.include_router(servicos.router)
app.include_router(pecas.router)
app.include_router(veiculos.router)
app.include_router(ordens_servico.router)
app.include_router(relatorios.router)
app.include_router(acompanhamento_publico.router)


def _openapi_da_api() -> dict[str, Any]:
    """Declara o esquema Bearer JWT para o botão "Authorize", mesmo sem rotas protegidas, e o
    corpo `ErroResponse` que a API devolve de fato no `422` e no `500`: o FastAPI documenta o
    `422` com o `HTTPValidationError`, que a API não usa (RNF-16)."""
    esquema = FastAPI.openapi(app)
    componentes = esquema.setdefault("components", {})
    componentes.setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    corpo_de_erro = {"application/json": {"schema": {"$ref": "#/components/schemas/ErroResponse"}}}
    for rota in esquema["paths"].values():
        for operacao in rota.values():
            respostas = operacao["responses"]
            if "422" in respostas:
                respostas["422"]["content"] = corpo_de_erro
                if respostas["422"]["description"] == "Validation Error":
                    respostas["422"]["description"] = "Entrada fora do formato esperado."
            respostas["500"] = {
                "description": "Erro interno, sem mensagem interna nem stack trace.",
                "content": corpo_de_erro,
            }
    for nome in ("HTTPValidationError", "ValidationError"):
        componentes["schemas"].pop(nome, None)
    return esquema


app.openapi = _openapi_da_api
