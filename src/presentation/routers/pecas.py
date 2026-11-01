from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from application.use_cases.ajustar_quantidade_fisica_da_peca import AjustarQuantidadeFisicaDaPeca
from application.use_cases.atualizar_peca import AtualizarPeca
from application.use_cases.cadastrar_peca import CadastrarPeca
from application.use_cases.detalhar_peca import DetalharPeca
from application.use_cases.excluir_peca import ExcluirPeca
from application.use_cases.listar_pecas import ListarPecas
from application.use_cases.repor_peca import ReporPeca
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.valor import Valor
from presentation.container import (
    obter_ajustar_quantidade_fisica_da_peca,
    obter_atualizar_peca,
    obter_cadastrar_peca,
    obter_detalhar_peca,
    obter_excluir_peca,
    obter_listar_pecas,
    obter_repor_peca,
)
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.erro import ErroResponse
from presentation.schemas.peca import (
    AjusteQuantidadeFisicaRequest,
    CadastrarPecaRequest,
    PecaRequest,
    PecaResponse,
    ReposicaoRequest,
)

router = APIRouter(
    prefix="/pecas",
    tags=["Peças e estoque"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

# RF-12: todos os perfis consultam; Mecânico e Gerente atualizam a quantidade em estoque; só o
# Gerente cria, altera os dados cadastrais e exclui.
_CONSULTA = [
    Depends(exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.MECANICO, PerfilUsuario.GERENTE))
]
_MOVIMENTACAO = [Depends(exigir_perfis(PerfilUsuario.MECANICO, PerfilUsuario.GERENTE))]
_ADMINISTRACAO = [Depends(exigir_perfis(PerfilUsuario.GERENTE))]

_DADOS_INVALIDOS = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErroResponse,
        "description": "Dado obrigatório vazio, preço, prazo ou quantidade negativos.",
    }
}
_QUANTIDADE_INVALIDA = {
    status.HTTP_400_BAD_REQUEST: {"model": ErroResponse, "description": "Quantidade inválida."}
}
_NAO_ENCONTRADA = {
    status.HTTP_404_NOT_FOUND: {"model": ErroResponse, "description": "Peça não encontrada."}
}
_CODIGO_JA_CADASTRADO = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": "Código de referência já cadastrado ou dados fora do formato.",
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
async def cadastrar_peca(
    dados: CadastrarPecaRequest,
    cadastrar: Annotated[CadastrarPeca, Depends(obter_cadastrar_peca, scope=_ANTES_DA_RESPOSTA)],
) -> PecaResponse:
    """Inclui uma peça, com a quantidade física inicial opcional (RF-12)."""
    peca, estoque = await cadastrar.executar(
        dados.codigo_referencia,
        dados.nome,
        Valor(dados.preco_unitario),
        dados.prazo_reposicao_dias,
        dados.quantidade_fisica_inicial,
    )
    return PecaResponse.de_entidades(peca, estoque)


@router.get("", dependencies=_CONSULTA)
async def listar_pecas(
    listar: Annotated[ListarPecas, Depends(obter_listar_pecas)],
) -> list[PecaResponse]:
    """Peças ativas, em ordem de nome, com o saldo disponível (RF-12)."""
    return [PecaResponse.de_entidades(peca, estoque) for peca, estoque in await listar.executar()]


@router.get("/{id}", dependencies=_CONSULTA, responses=_NAO_ENCONTRADA)
async def detalhar_peca(
    id: UUID,
    detalhar: Annotated[DetalharPeca, Depends(obter_detalhar_peca)],
) -> PecaResponse:
    """Dados da peça com as quantidades física e reservada e o saldo disponível (RF-12)."""
    return PecaResponse.de_entidades(*await detalhar.executar(id))


@router.put(
    "/{id}",
    dependencies=_ADMINISTRACAO,
    responses=_DADOS_INVALIDOS | _NAO_ENCONTRADA | _CODIGO_JA_CADASTRADO,
)
async def atualizar_peca(
    id: UUID,
    dados: PecaRequest,
    atualizar: Annotated[AtualizarPeca, Depends(obter_atualizar_peca, scope=_ANTES_DA_RESPOSTA)],
) -> PecaResponse:
    """Altera os dados cadastrais; as OS já orçadas não mudam (RF-12, RF-17)."""
    peca, estoque = await atualizar.executar(
        id,
        dados.codigo_referencia,
        dados.nome,
        Valor(dados.preco_unitario),
        dados.prazo_reposicao_dias,
    )
    return PecaResponse.de_entidades(peca, estoque)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_ADMINISTRACAO,
    responses=_NAO_ENCONTRADA
    | {
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErroResponse,
            "description": "A peça está pendente em alguma OS.",
        }
    },
)
async def excluir_peca(
    id: UUID,
    excluir: Annotated[ExcluirPeca, Depends(obter_excluir_peca, scope=_ANTES_DA_RESPOSTA)],
) -> None:
    """Exclusão lógica: a peça sai da listagem e as reservas existentes continuam (RF-12)."""
    await excluir.executar(id)


@router.post(
    "/{id}/reposicao",
    dependencies=_MOVIMENTACAO,
    responses=_QUANTIDADE_INVALIDA | _NAO_ENCONTRADA,
)
async def repor_peca(
    id: UUID,
    dados: ReposicaoRequest,
    repor: Annotated[ReporPeca, Depends(obter_repor_peca, scope=_ANTES_DA_RESPOSTA)],
) -> PecaResponse:
    """Soma a quantidade recebida à quantidade física (RF-12, RF-19)."""
    return PecaResponse.de_entidades(*await repor.executar(id, dados.quantidade))


@router.put(
    "/{id}/quantidade-fisica",
    dependencies=_MOVIMENTACAO,
    responses=_QUANTIDADE_INVALIDA
    | _NAO_ENCONTRADA
    | {
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErroResponse,
            "description": "A nova quantidade física ficaria abaixo da reservada.",
        }
    },
)
async def ajustar_quantidade_fisica(
    id: UUID,
    dados: AjusteQuantidadeFisicaRequest,
    ajustar: Annotated[
        AjustarQuantidadeFisicaDaPeca,
        Depends(obter_ajustar_quantidade_fisica_da_peca, scope=_ANTES_DA_RESPOSTA),
    ],
) -> PecaResponse:
    """Corrige a quantidade física por perda, quebra ou inventário (RF-12)."""
    return PecaResponse.de_entidades(*await ajustar.executar(id, dados.quantidade_fisica))
