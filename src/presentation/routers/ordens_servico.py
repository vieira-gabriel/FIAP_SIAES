from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from application.ports.token_service import UsuarioAutenticado
from application.use_cases.criar_os import (
    CriarOS,
    DadosDoNovoCliente,
    DadosDoNovoVeiculo,
)
from application.use_cases.detalhar_ordem_servico import DetalharOrdemServico
from application.use_cases.listar_ordens_servico import CriteriosDaListagem, ListarOrdensServico
from domain.value_objects.documento import Documento
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS
from presentation.container import (
    obter_criar_os,
    obter_detalhar_ordem_servico,
    obter_listar_ordens_servico,
)
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.erro import ErroResponse
from presentation.schemas.ordem_servico import (
    AbrirOSRequest,
    OSDetalheResponse,
    OSResponse,
    OSResumoResponse,
)

router = APIRouter(
    prefix="/ordens-servico",
    tags=["Ordens de serviço"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

# RF-13: a abertura é do Atendente e do Gerente.
_ABERTURA = exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.GERENTE)
# RF-14, RF-15: a consulta é de todos os perfis.
_CONSULTA = exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.MECANICO, PerfilUsuario.GERENTE)

_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErroResponse,
        "description": "Cliente ou veículo não cadastrado e sem os dados para cadastrá-lo.",
    }
}
_REGRA_VIOLADA = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": "Placa de outro cliente, documento já cadastrado ou dados fora do formato.",
    }
}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=_NAO_ENCONTRADO | _REGRA_VIOLADA,
)
async def abrir_os(
    dados: AbrirOSRequest,
    usuario: Annotated[UsuarioAutenticado, Depends(_ABERTURA)],
    abrir: Annotated[CriarOS, Depends(obter_criar_os, scope="function")],
) -> OSResponse:
    """Abre a OS em `RECEBIDA`. Cliente e veículo que não existem são cadastrados se os dados
    forem informados no corpo (RF-04, RF-07, RF-13)."""
    os = await abrir.executar(
        Documento.de_texto(dados.documento),
        Placa(dados.placa),
        usuario.usuario_id,
        cliente_novo=(
            DadosDoNovoCliente(dados.cliente.nome, dados.cliente.email, dados.cliente.telefone)
            if dados.cliente
            else None
        ),
        veiculo_novo=(
            DadosDoNovoVeiculo(dados.veiculo.marca, dados.veiculo.modelo, dados.veiculo.ano)
            if dados.veiculo
            else None
        ),
    )
    return OSResponse.de_entidade(os)


@router.get("")
async def listar_os(
    _usuario: Annotated[UsuarioAutenticado, Depends(_CONSULTA)],
    listar: Annotated[ListarOrdensServico, Depends(obter_listar_ordens_servico)],
    documento: str | None = None,
    placa: str | None = None,
    status: StatusOS | None = None,
    mecanico_id: UUID | None = None,
    abertura_de: datetime | None = None,
    abertura_ate: datetime | None = None,
) -> list[OSResumoResponse]:
    """As OS que atendem a todos os filtros informados, das mais recentes às mais antigas
    (RF-14). Sem filtros, lista todas."""
    resumos = await listar.executar(
        CriteriosDaListagem(
            documento=Documento.de_texto(documento) if documento else None,
            placa=Placa(placa) if placa else None,
            status=status,
            mecanico_id=mecanico_id,
            abertura_de=abertura_de,
            abertura_ate=abertura_ate,
        )
    )
    return [OSResumoResponse.de_resumo(resumo) for resumo in resumos]


@router.get(
    "/{id}",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErroResponse, "description": "OS não encontrada."}
    },
)
async def detalhar_os(
    id: UUID,
    _usuario: Annotated[UsuarioAutenticado, Depends(_CONSULTA)],
    detalhar: Annotated[DetalharOrdemServico, Depends(obter_detalhar_ordem_servico)],
) -> OSDetalheResponse:
    """Todos os dados da OS, com itens, quantidades reservadas e pendentes, histórico e a
    estimativa de entrega do momento da consulta (RF-15, RF-25)."""
    detalhe = await detalhar.executar(id, datetime.now(UTC))
    return OSDetalheResponse.de_detalhe(detalhe)
