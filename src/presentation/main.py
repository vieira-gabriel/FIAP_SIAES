from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from presentation.container import (
    encerrar_dependencias,
    executar_carga_inicial,
    montar_dependencias,
)
from presentation.routers import autenticacao, saude

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
app.include_router(saude.router)
app.include_router(autenticacao.router)


def _openapi_com_esquema_bearer() -> dict[str, Any]:
    """Declara o esquema Bearer JWT para o botão "Authorize", mesmo sem rotas protegidas."""
    esquema = FastAPI.openapi(app)
    esquema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    return esquema


app.openapi = _openapi_com_esquema_bearer
