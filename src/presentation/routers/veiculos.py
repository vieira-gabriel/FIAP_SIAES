from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from application.use_cases.atualizar_veiculo import AtualizarVeiculo
from application.use_cases.cadastrar_veiculo import CadastrarVeiculo
from application.use_cases.detalhar_veiculo import DetalharVeiculo
from application.use_cases.excluir_veiculo import ExcluirVeiculo
from application.use_cases.listar_veiculos import ListarVeiculos
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from presentation.container import (
    obter_atualizar_veiculo,
    obter_cadastrar_veiculo,
    obter_detalhar_veiculo,
    obter_excluir_veiculo,
    obter_listar_veiculos,
)
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.erro import ErroResponse
from presentation.schemas.veiculo import (
    AtualizarVeiculoRequest,
    CadastrarVeiculoRequest,
    VeiculoResponse,
)

router = APIRouter(
    prefix="/veiculos",
    tags=["Veículos"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

# RF-07: Atendente e Gerente cadastram e atualizam; o Mecânico só consulta. RF-09: Atendente e
# Gerente excluem.
_GRAVACAO = [Depends(exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.GERENTE))]
_CONSULTA = [
    Depends(exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.GERENTE, PerfilUsuario.MECANICO))
]

_DADOS_INVALIDOS = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErroResponse,
        "description": "Placa fora dos padrões ABC1234 e ABC1D23 ou marca, modelo ou ano inválido.",
    }
}
_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {"model": ErroResponse, "description": "Veículo não encontrado."}
}
_CLIENTE_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErroResponse,
        "description": "Cliente proprietário inexistente ou excluído.",
    }
}
_PLACA_JA_CADASTRADA = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": "Placa de outro veículo ativo ou dados fora do formato.",
    }
}

# As gravações confirmam a transação antes de responder; sem `scope="function"`, o commit
# aconteceria depois de o cliente já ter recebido o 201.
_ANTES_DA_RESPOSTA = "function"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=_GRAVACAO,
    responses=_DADOS_INVALIDOS | _CLIENTE_NAO_ENCONTRADO | _PLACA_JA_CADASTRADA,
)
async def cadastrar_veiculo(
    dados: CadastrarVeiculoRequest,
    cadastrar: Annotated[
        CadastrarVeiculo, Depends(obter_cadastrar_veiculo, scope=_ANTES_DA_RESPOSTA)
    ],
) -> VeiculoResponse:
    """Cadastro de veículo vinculado a um cliente ativo (RF-07, RF-08)."""
    veiculo = await cadastrar.executar(
        dados.cliente_id, Placa(dados.placa), dados.marca, dados.modelo, dados.ano
    )
    return VeiculoResponse.de_entidade(veiculo)


@router.get("", dependencies=_CONSULTA)
async def listar_veiculos(
    listar: Annotated[ListarVeiculos, Depends(obter_listar_veiculos)],
    cliente_id: UUID | None = None,
) -> list[VeiculoResponse]:
    """Veículos ativos, em ordem de placa; com `cliente_id`, só os desse cliente (RF-07, RF-09)."""
    return [VeiculoResponse.de_entidade(veiculo) for veiculo in await listar.executar(cliente_id)]


@router.get("/{id}", dependencies=_CONSULTA, responses=_NAO_ENCONTRADO)
async def detalhar_veiculo(
    id: UUID,
    detalhar: Annotated[DetalharVeiculo, Depends(obter_detalhar_veiculo)],
) -> VeiculoResponse:
    return VeiculoResponse.de_entidade(await detalhar.executar(id))


@router.put(
    "/{id}",
    dependencies=_GRAVACAO,
    responses=_DADOS_INVALIDOS | _NAO_ENCONTRADO | _PLACA_JA_CADASTRADA,
)
async def atualizar_veiculo(
    id: UUID,
    dados: AtualizarVeiculoRequest,
    atualizar: Annotated[
        AtualizarVeiculo, Depends(obter_atualizar_veiculo, scope=_ANTES_DA_RESPOSTA)
    ],
) -> VeiculoResponse:
    """Atualização dos dados de um veículo ativo; o proprietário não muda (RF-07, RF-08)."""
    veiculo = await atualizar.executar(id, Placa(dados.placa), dados.marca, dados.modelo, dados.ano)
    return VeiculoResponse.de_entidade(veiculo)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_GRAVACAO,
    responses=_NAO_ENCONTRADO,
)
async def excluir_veiculo(
    id: UUID,
    excluir: Annotated[ExcluirVeiculo, Depends(obter_excluir_veiculo, scope=_ANTES_DA_RESPOSTA)],
) -> None:
    """Exclusão lógica: o veículo sai da listagem e as OS dele são preservadas (RF-09)."""
    await excluir.executar(id)
