from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from application.ports.token_service import UsuarioAutenticado
from application.use_cases.alterar_senha_do_usuario import AlterarSenhaDoUsuario
from application.use_cases.atualizar_usuario import AtualizarUsuario
from application.use_cases.cadastrar_usuario import CadastrarUsuario
from application.use_cases.desativar_usuario import DesativarUsuario
from application.use_cases.detalhar_usuario import DetalharUsuario
from application.use_cases.listar_usuarios import ListarUsuarios
from application.use_cases.reativar_usuario import ReativarUsuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.container import (
    obter_alterar_senha_do_usuario,
    obter_atualizar_usuario,
    obter_cadastrar_usuario,
    obter_desativar_usuario,
    obter_detalhar_usuario,
    obter_listar_usuarios,
    obter_reativar_usuario,
)
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.erro import ErroResponse
from presentation.schemas.usuario import (
    SenhaRequest,
    UsuarioAtualizacaoRequest,
    UsuarioCadastroRequest,
    UsuarioResponse,
)

# RF-03: toda a gestão de usuários é exclusiva do Gerente.
_somente_gerente = exigir_perfis(PerfilUsuario.GERENTE)
Gerente = Annotated[UsuarioAutenticado, Depends(_somente_gerente)]

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"],
    dependencies=[Depends(_somente_gerente)],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

_DADOS_INVALIDOS = {
    status.HTTP_400_BAD_REQUEST: {"model": ErroResponse, "description": "Nome ou e-mail inválido."}
}
_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {"model": ErroResponse, "description": "Usuário não encontrado."}
}
_REGRA_VIOLADA = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": "E-mail já cadastrado, alteração do próprio acesso ou dados inválidos.",
    }
}

# As gravações confirmam a transação antes de responder (guia, seção 5.5).
_ANTES_DA_RESPOSTA = "function"


@router.post("", status_code=status.HTTP_201_CREATED, responses=_DADOS_INVALIDOS | _REGRA_VIOLADA)
async def cadastrar_usuario(
    dados: UsuarioCadastroRequest,
    cadastrar: Annotated[
        CadastrarUsuario, Depends(obter_cadastrar_usuario, scope=_ANTES_DA_RESPOSTA)
    ],
) -> UsuarioResponse:
    """Cria o acesso de um funcionário com o perfil escolhido; a senha é gravada como hash."""
    usuario = await cadastrar.executar(dados.nome, dados.email, dados.senha, dados.perfil)
    return UsuarioResponse.de_entidade(usuario)


@router.get("")
async def listar_usuarios(
    listar: Annotated[ListarUsuarios, Depends(obter_listar_usuarios)],
) -> list[UsuarioResponse]:
    """Ativos e desativados, em ordem de nome."""
    return [UsuarioResponse.de_entidade(usuario) for usuario in await listar.executar()]


@router.get("/{id}", responses=_NAO_ENCONTRADO)
async def detalhar_usuario(
    id: UUID,
    detalhar: Annotated[DetalharUsuario, Depends(obter_detalhar_usuario)],
) -> UsuarioResponse:
    """Dados do usuário, ativo ou desativado, sem a senha (RF-03)."""
    return UsuarioResponse.de_entidade(await detalhar.executar(id))


@router.put("/{id}", responses=_DADOS_INVALIDOS | _NAO_ENCONTRADO | _REGRA_VIOLADA)
async def atualizar_usuario(
    id: UUID,
    dados: UsuarioAtualizacaoRequest,
    gerente: Gerente,
    atualizar: Annotated[
        AtualizarUsuario, Depends(obter_atualizar_usuario, scope=_ANTES_DA_RESPOSTA)
    ],
) -> UsuarioResponse:
    """Nome, e-mail e perfil. O Gerente não muda o próprio perfil."""
    usuario = await atualizar.executar(
        id, dados.nome, dados.email, dados.perfil, gerente.usuario_id
    )
    return UsuarioResponse.de_entidade(usuario)


@router.put(
    "/{id}/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NAO_ENCONTRADO | _REGRA_VIOLADA,
)
async def alterar_senha_do_usuario(
    id: UUID,
    dados: SenhaRequest,
    alterar_senha: Annotated[
        AlterarSenhaDoUsuario,
        Depends(obter_alterar_senha_do_usuario, scope=_ANTES_DA_RESPOSTA),
    ],
) -> None:
    """Nova senha com pelo menos 8 caracteres; só o hash é gravado."""
    await alterar_senha.executar(id, dados.senha)


@router.post(
    "/{id}/desativar",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NAO_ENCONTRADO | _REGRA_VIOLADA,
)
async def desativar_usuario(
    id: UUID,
    gerente: Gerente,
    desativar: Annotated[
        DesativarUsuario, Depends(obter_desativar_usuario, scope=_ANTES_DA_RESPOSTA)
    ],
) -> None:
    """O usuário desativado não faz login. O Gerente não desativa o próprio acesso."""
    await desativar.executar(id, gerente.usuario_id)


@router.post("/{id}/reativar", status_code=status.HTTP_204_NO_CONTENT, responses=_NAO_ENCONTRADO)
async def reativar_usuario(
    id: UUID,
    reativar: Annotated[ReativarUsuario, Depends(obter_reativar_usuario, scope=_ANTES_DA_RESPOSTA)],
) -> None:
    """Devolve o acesso ao usuário desativado (RF-03)."""
    await reativar.executar(id)
