from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from application.use_cases.aprovar_orcamento import AprovarOrcamento
from application.use_cases.consultar_os_publica import ConsultarOSPublica
from presentation.container import obter_aprovar_orcamento, obter_consultar_os_publica
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


@router.post(
    "/aprovacao",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErroResponse,
            "description": "Número inexistente ou documento de outro titular, sem distinção.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErroResponse,
            "description": "A OS não está em `AGUARDANDO_APROVACAO`.",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErroResponse,
            "description": "Limite de requisições por minuto, por IP, excedido.",
        },
    },
)
@limite_publico
async def aprovar_orcamento(
    request: Request,
    dados: ConsultaPublicaRequest,
    aprovar: Annotated[AprovarOrcamento, Depends(obter_aprovar_orcamento, scope="function")],
) -> AcompanhamentoResponse:
    """O cliente aprova o orçamento: a OS passa a `AGUARDANDO_EXECUCAO`, ou a `AGUARDANDO_PECA` se
    houver peça pendente (RF-26). Identifica-se como na consulta, pelo número e pelo CPF/CNPJ."""
    acompanhamento = await aprovar.executar(dados.numero, dados.documento, datetime.now(UTC))
    return AcompanhamentoResponse.de_acompanhamento(acompanhamento)
