from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from application.use_cases.atualizar_servico import AtualizarServico
from application.use_cases.cadastrar_servico import CadastrarServico
from application.use_cases.detalhar_servico import DetalharServico
from application.use_cases.excluir_servico import ExcluirServico
from application.use_cases.listar_servicos import ListarServicos
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.valor import Valor
from presentation.container import (
    obter_atualizar_servico,
    obter_cadastrar_servico,
    obter_detalhar_servico,
    obter_excluir_servico,
    obter_listar_servicos,
)
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.erro import ErroResponse
from presentation.schemas.servico import ServicoRequest, ServicoResponse

router = APIRouter(
    prefix="/servicos",
    tags=["Catálogo de serviços"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

# RF-10: todos os perfis consultam o catálogo. RF-11: só o Gerente o administra.
_CONSULTA = [
    Depends(exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.MECANICO, PerfilUsuario.GERENTE))
]
_ADMINISTRACAO = [Depends(exigir_perfis(PerfilUsuario.GERENTE))]

_DADOS_INVALIDOS = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErroResponse,
        "description": "Dado obrigatório vazio, valor base negativo ou tempo estimado negativo.",
    }
}
_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {"model": ErroResponse, "description": "Serviço não encontrado."}
}
_CODIGO_JA_CADASTRADO = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": "Código já cadastrado ou dados fora do formato.",
    }
}

# As gravações confirmam a transação antes de responder (guia, seção 5.5).
_ANTES_DA_RESPOSTA = "function"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=_ADMINISTRACAO,
    responses=_DADOS_INVALIDOS | _CODIGO_JA_CADASTRADO,
)
async def cadastrar_servico(
    dados: ServicoRequest,
    cadastrar: Annotated[
        CadastrarServico, Depends(obter_cadastrar_servico, scope=_ANTES_DA_RESPOSTA)
    ],
) -> ServicoResponse:
    """Inclui um serviço no catálogo, com o tempo estimado em minutos (RF-11)."""
    servico = await cadastrar.executar(
        dados.codigo,
        dados.nome,
        dados.descricao,
        Valor(dados.valor_base),
        dados.tempo_estimado_minutos,
    )
    return ServicoResponse.de_entidade(servico)


@router.get("", dependencies=_CONSULTA)
async def listar_servicos(
    listar: Annotated[ListarServicos, Depends(obter_listar_servicos)],
) -> list[ServicoResponse]:
    """Serviços ativos do catálogo, em ordem de nome (RF-10)."""
    return [ServicoResponse.de_entidade(servico) for servico in await listar.executar()]


@router.get("/{id}", dependencies=_CONSULTA, responses=_NAO_ENCONTRADO)
async def detalhar_servico(
    id: UUID,
    detalhar: Annotated[DetalharServico, Depends(obter_detalhar_servico)],
) -> ServicoResponse:
    return ServicoResponse.de_entidade(await detalhar.executar(id))


@router.put(
    "/{id}",
    dependencies=_ADMINISTRACAO,
    responses=_DADOS_INVALIDOS | _NAO_ENCONTRADO | _CODIGO_JA_CADASTRADO,
)
async def atualizar_servico(
    id: UUID,
    dados: ServicoRequest,
    atualizar: Annotated[
        AtualizarServico, Depends(obter_atualizar_servico, scope=_ANTES_DA_RESPOSTA)
    ],
) -> ServicoResponse:
    """Altera os dados, o valor base e o tempo estimado; as OS já orçadas não mudam (RF-11)."""
    servico = await atualizar.executar(
        id,
        dados.codigo,
        dados.nome,
        dados.descricao,
        Valor(dados.valor_base),
        dados.tempo_estimado_minutos,
    )
    return ServicoResponse.de_entidade(servico)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_ADMINISTRACAO,
    responses=_NAO_ENCONTRADO,
)
async def excluir_servico(
    id: UUID,
    excluir: Annotated[ExcluirServico, Depends(obter_excluir_servico, scope=_ANTES_DA_RESPOSTA)],
) -> None:
    """Exclusão lógica: o serviço sai do catálogo e não entra em novas OS (RF-11)."""
    await excluir.executar(id)
