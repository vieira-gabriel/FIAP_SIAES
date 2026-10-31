from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status

from application.use_cases.consultar_os_publica import ConsultarOSPublica
from presentation.container import obter_consultar_os_publica
from presentation.schemas.acompanhamento_publico import (
    AcompanhamentoResponse,
    ConsultaPublicaRequest,
)
from presentation.schemas.erro import ErroResponse

# Rota pública (RF-25): sem JWT. O rate limiting (RNF-05) é da issue #97.
router = APIRouter(prefix="/acompanhamento", tags=["Acompanhamento público"])


@router.post(
    "",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErroResponse,
            "description": "Número inexistente ou documento de outro titular, sem distinção.",
        }
    },
)
async def consultar_os(
    dados: ConsultaPublicaRequest,
    consultar: Annotated[ConsultarOSPublica, Depends(obter_consultar_os_publica)],
) -> AcompanhamentoResponse:
    """Status, serviços, peças pendentes, valor total e estimativa de entrega da OS (RF-25).

    O CPF/CNPJ vai no corpo, e não na URL, para não ficar nos logs de acesso.
    """
    acompanhamento = await consultar.executar(dados.numero, dados.documento, datetime.now(UTC))
    return AcompanhamentoResponse.de_acompanhamento(acompanhamento)
