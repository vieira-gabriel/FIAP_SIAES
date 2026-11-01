from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status

from application.use_cases.gerar_relatorio_de_tempos import GerarRelatorioDeTempos
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.container import obter_gerar_relatorio_de_tempos
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.erro import ErroResponse
from presentation.schemas.relatorio import RelatorioDeTemposResponse

router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

# RF-27: o relatório de tempos é só do Gerente.
_GERENTE = [Depends(exigir_perfis(PerfilUsuario.GERENTE))]


@router.get(
    "/tempos-medios",
    dependencies=_GERENTE,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErroResponse,
            "description": "Período sem fuso horário ou com início posterior ao fim.",
        }
    },
)
async def relatorio_de_tempos_medios(
    gerar: Annotated[GerarRelatorioDeTempos, Depends(obter_gerar_relatorio_de_tempos)],
    finalizadas_de: datetime | None = None,
    finalizadas_ate: datetime | None = None,
) -> RelatorioDeTemposResponse:
    """Tempos médios das OS finalizadas no período (RF-27), em segundos, agrupados por mês da
    finalização: execução (por mecânico), espera por peça e total. Sem período, considera todas
    as OS finalizadas."""
    return RelatorioDeTemposResponse.de_relatorio(
        await gerar.executar(finalizadas_de, finalizadas_ate)
    )
