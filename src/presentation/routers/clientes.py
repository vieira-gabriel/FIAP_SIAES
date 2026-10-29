from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from application.use_cases.atualizar_cliente import AtualizarCliente
from application.use_cases.cadastrar_cliente import CadastrarCliente
from application.use_cases.detalhar_cliente import DetalharCliente
from application.use_cases.excluir_cliente import ExcluirCliente
from application.use_cases.listar_clientes import ListarClientes
from domain.value_objects.documento import Documento
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.container import (
    obter_atualizar_cliente,
    obter_cadastrar_cliente,
    obter_detalhar_cliente,
    obter_excluir_cliente,
    obter_listar_clientes,
)
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.cliente import ClienteRequest, ClienteResponse
from presentation.schemas.erro import ErroResponse

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

# RF-04: Atendente e Gerente cadastram e atualizam; o Mecânico só consulta. RF-06: só o Gerente
# exclui.
_GRAVACAO = [Depends(exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.GERENTE))]
_CONSULTA = [
    Depends(exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.GERENTE, PerfilUsuario.MECANICO))
]
_EXCLUSAO = [Depends(exigir_perfis(PerfilUsuario.GERENTE))]

_DOCUMENTO_INVALIDO = {
    status.HTTP_400_BAD_REQUEST: {"model": ErroResponse, "description": "CPF ou CNPJ inválido."}
}
_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {"model": ErroResponse, "description": "Cliente não encontrado."}
}
_DOCUMENTO_JA_CADASTRADO = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": "Documento já cadastrado ou dados fora do formato.",
    }
}

# As gravações confirmam a transação antes de responder; sem `scope="function"`, o commit
# aconteceria depois de o cliente já ter recebido o 201.
_ANTES_DA_RESPOSTA = "function"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=_GRAVACAO,
    responses=_DOCUMENTO_INVALIDO | _DOCUMENTO_JA_CADASTRADO,
)
async def cadastrar_cliente(
    dados: ClienteRequest,
    cadastrar: Annotated[
        CadastrarCliente, Depends(obter_cadastrar_cliente, scope=_ANTES_DA_RESPOSTA)
    ],
) -> ClienteResponse:
    """Cadastro de cliente pessoa física ou jurídica (RF-04, RF-05)."""
    cliente = await cadastrar.executar(
        dados.nome, Documento.de_texto(dados.documento), dados.email, dados.telefone
    )
    return ClienteResponse.de_entidade(cliente)


@router.get("", dependencies=_CONSULTA)
async def listar_clientes(
    listar: Annotated[ListarClientes, Depends(obter_listar_clientes)],
) -> list[ClienteResponse]:
    """Clientes ativos, em ordem de nome (RF-04, RF-06)."""
    return [ClienteResponse.de_entidade(cliente) for cliente in await listar.executar()]


@router.get("/{id}", dependencies=_CONSULTA, responses=_NAO_ENCONTRADO)
async def detalhar_cliente(
    id: UUID,
    detalhar: Annotated[DetalharCliente, Depends(obter_detalhar_cliente)],
) -> ClienteResponse:
    return ClienteResponse.de_entidade(await detalhar.executar(id))


@router.put(
    "/{id}",
    dependencies=_GRAVACAO,
    responses=_DOCUMENTO_INVALIDO | _NAO_ENCONTRADO | _DOCUMENTO_JA_CADASTRADO,
)
async def atualizar_cliente(
    id: UUID,
    dados: ClienteRequest,
    atualizar: Annotated[
        AtualizarCliente, Depends(obter_atualizar_cliente, scope=_ANTES_DA_RESPOSTA)
    ],
) -> ClienteResponse:
    """Atualização dos dados de um cliente ativo (RF-04, RF-05)."""
    cliente = await atualizar.executar(
        id, dados.nome, Documento.de_texto(dados.documento), dados.email, dados.telefone
    )
    return ClienteResponse.de_entidade(cliente)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_EXCLUSAO,
    responses=_NAO_ENCONTRADO,
)
async def excluir_cliente(
    id: UUID,
    excluir: Annotated[ExcluirCliente, Depends(obter_excluir_cliente, scope=_ANTES_DA_RESPOSTA)],
) -> None:
    """Exclusão lógica: o cliente sai da listagem e as OS dele são preservadas (RF-06)."""
    await excluir.executar(id)
