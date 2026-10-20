"""Validação do token e checagem de perfil nas rotas administrativas e operacionais.

Uso em uma rota:

    @router.post("/servicos", dependencies=[Depends(exigir_perfis(PerfilUsuario.GERENTE))])

ou, quando a rota precisa do usuário logado:

    def rota(usuario: Annotated[UsuarioAutenticado, Depends(obter_usuario_autenticado)]): ...

A implementação de `TokenService` e o caso de uso `AutenticarUsuario` são registrados em
`app.state.token_service` e `app.state.autenticar_usuario` no ponto de montagem da aplicação
(`presentation/container.py`); assim este módulo não importa a infraestrutura (guia, seção 2.1).
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.ports.token_service import TokenInvalido, TokenService, UsuarioAutenticado
from application.use_cases.autenticar_usuario import AutenticarUsuario
from domain.value_objects.perfil_usuario import PerfilUsuario

_bearer = HTTPBearer(auto_error=False)


def obter_token_service(request: Request) -> TokenService:
    return request.app.state.token_service


def obter_autenticar_usuario(request: Request) -> AutenticarUsuario:
    return request.app.state.autenticar_usuario


def obter_usuario_autenticado(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    token_service: Annotated[TokenService, Depends(obter_token_service)],
) -> UsuarioAutenticado:
    """Sem token ou com token inválido/expirado: `401` (RF-01, RNF-03)."""
    if credenciais is None:
        raise _nao_autenticado("Token de acesso ausente.")
    try:
        return token_service.validar(credenciais.credentials)
    except TokenInvalido as erro:
        raise _nao_autenticado("Token de acesso inválido ou expirado.") from erro


def exigir_perfis(*perfis: PerfilUsuario) -> Callable[..., UsuarioAutenticado]:
    """Perfil do token sem permissão para a rota: `403` (RF-02, RNF-03)."""
    if not perfis:
        raise ValueError("Informe ao menos um perfil autorizado.")
    permitidos = frozenset(perfis)

    def verificar_perfil(
        usuario: Annotated[UsuarioAutenticado, Depends(obter_usuario_autenticado)],
    ) -> UsuarioAutenticado:
        if usuario.perfil not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil sem permissão para esta operação.",
            )
        return usuario

    return verificar_perfil


def _nao_autenticado(detalhe: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalhe,
        headers={"WWW-Authenticate": "Bearer"},
    )
