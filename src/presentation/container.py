from fastapi import FastAPI, Request

from application.ports.token_service import TokenService
from application.ports.verificador_do_banco import VerificadorDoBanco
from infrastructure.config import carregar_configuracao
from infrastructure.database.engine import criar_engine, criar_fabrica_de_sessoes
from infrastructure.database.verificador_do_banco import VerificadorDoBancoSqlAlchemy
from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from infrastructure.security.jwt_token_service import JwtTokenService


def montar_dependencias(app: FastAPI) -> None:
    """Falha na subida, antes de aceitar requisições, se faltar variável obrigatória (RNF-06)."""
    configuracao = carregar_configuracao()
    engine = criar_engine(
        host=configuracao.postgres_host,
        porta=configuracao.postgres_port,
        banco=configuracao.postgres_db,
        usuario=configuracao.postgres_user,
        senha=configuracao.postgres_password.get_secret_value(),
    )
    app.state.engine = engine
    app.state.fabrica_de_sessoes = criar_fabrica_de_sessoes(engine)
    app.state.token_service = JwtTokenService(
        configuracao.jwt_secret_key.get_secret_value(),
        expiracao_horas=configuracao.jwt_expiration_hours,
    )
    app.state.password_hasher = BcryptPasswordHasher()
    app.state.verificador_do_banco = VerificadorDoBancoSqlAlchemy(engine)


async def encerrar_dependencias(app: FastAPI) -> None:
    await app.state.engine.dispose()


def obter_token_service(request: Request) -> TokenService:
    return request.app.state.token_service


def obter_verificador_do_banco(request: Request) -> VerificadorDoBanco:
    return request.app.state.verificador_do_banco
