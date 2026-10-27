from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from application.ports.verificador_do_banco import VerificadorDoBanco
from presentation.container import obter_verificador_do_banco
from presentation.schemas.saude import SaudeResponse

router = APIRouter(tags=["Health Check"])


@router.get(
    "/health",
    response_model=SaudeResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": SaudeResponse,
            "description": "Banco de dados indisponível.",
        },
    },
)
async def health_check(
    resposta: Response,
    verificador: Annotated[VerificadorDoBanco, Depends(obter_verificador_do_banco)],
) -> SaudeResponse:
    """Estado da aplicação e da conexão com o banco; `503` quando o banco não responde."""
    if await verificador.esta_disponivel():
        return SaudeResponse(
            status="online", banco="disponivel", message="Serviço operando normalmente."
        )
    resposta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return SaudeResponse(
        status="indisponivel", banco="indisponivel", message="Banco de dados indisponível."
    )
