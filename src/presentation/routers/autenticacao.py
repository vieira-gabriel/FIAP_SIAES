from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from application.use_cases.autenticar_usuario import AutenticarUsuario
from domain.exceptions import CredenciaisInvalidas
from presentation.container import obter_autenticar_usuario
from presentation.schemas.autenticacao import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "E-mail ou senha inválidos."}},
)
async def login(
    dados: LoginRequest,
    autenticar: Annotated[AutenticarUsuario, Depends(obter_autenticar_usuario)],
) -> TokenResponse:
    """Login de usuário interno com e-mail e senha (RF-01)."""
    try:
        token = await autenticar.executar(dados.email, dados.senha)
    except CredenciaisInvalidas as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(erro),
            headers={"WWW-Authenticate": "Bearer"},
        ) from erro
    return TokenResponse(access_token=token)
