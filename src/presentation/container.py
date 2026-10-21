from fastapi import FastAPI

from infrastructure.config import carregar_configuracao
from infrastructure.security.jwt_token_service import JwtTokenService


def montar_dependencias(app: FastAPI) -> None:
    """Falha na subida, antes de aceitar requisições, se faltar variável obrigatória (RNF-06)."""
    configuracao = carregar_configuracao()
    app.state.token_service = JwtTokenService(
        configuracao.jwt_secret_key.get_secret_value(),
        expiracao_horas=configuracao.jwt_expiration_hours,
    )
