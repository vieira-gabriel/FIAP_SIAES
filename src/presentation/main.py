from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from presentation.container import montar_dependencias


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    montar_dependencias(app)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {
        "status": "online",
        "message": "Serviço operando normalmente.",
    }
