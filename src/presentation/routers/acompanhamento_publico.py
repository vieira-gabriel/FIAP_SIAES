from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from application.use_cases.consultar_os_publica import ConsultarOSPublica
from presentation.container import obter_consultar_os_publica
from presentation.middlewares.rate_limit import limite_publico
from presentation.schemas.acompanhamento_publico import (
    AcompanhamentoResponse,
    ConsultaPublicaRequest,
)
from presentation.schemas.erro import ErroResponse

# Rota pública (RF-25): sem JWT, com limite de requisições por IP (RNF-05).
router = APIRouter(prefix="/acompanhamento", tags=["Acompanhamento público"])


@router.post(
    "",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErroResponse,
            "description": "Número inexistente ou documento de outro titular, sem distinção.",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErroResponse,
            "description": "Limite de requisições por minuto, por IP, excedido.",
        },
    },
)
@limite_publico
async def consultar_os(
    request: Request,
    dados: ConsultaPublicaRequest,
    consultar: Annotated[ConsultarOSPublica, Depends(obter_consultar_os_publica)],
) -> AcompanhamentoResponse:
    """Status, serviços, peças pendentes, valor total e estimativa de entrega da OS (RF-25).

    O CPF/CNPJ vai no corpo, e não na URL, para não ficar nos logs de acesso.
    """
    acompanhamento = await consultar.executar(dados.numero, dados.documento, datetime.now(UTC))
    return AcompanhamentoResponse.de_acompanhamento(acompanhamento)
