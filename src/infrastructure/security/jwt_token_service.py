from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from application.ports.token_service import TokenInvalido, TokenService, UsuarioAutenticado
from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario

_ALGORITMO = "HS256"
_CLAIMS_OBRIGATORIAS = ["sub", "role", "exp", "iat"]


class JwtTokenService(TokenService):
    """Tokens JWT assinados com HS256, com a claim `role` e expiração (RF-01, RNF-03).

    A chave de assinatura vem de variável de ambiente (`JWT_SECRET_KEY`, RNF-06) e é
    repassada por quem monta as dependências da aplicação.
    """

    def __init__(
        self,
        chave_secreta: str,
        expiracao_horas: int = 24,
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        if not chave_secreta:
            raise ValueError("A chave de assinatura do JWT é obrigatória (JWT_SECRET_KEY).")
        if expiracao_horas <= 0:
            raise ValueError("A expiração do JWT deve ser maior que zero.")
        self._chave_secreta = chave_secreta
        self._expiracao = timedelta(hours=expiracao_horas)
        self._relogio = relogio

    def emitir(self, usuario: Usuario) -> str:
        agora = self._relogio()
        claims = {
            "sub": str(usuario.id),
            "role": usuario.perfil.value,
            "iat": agora,
            "exp": agora + self._expiracao,
        }
        return jwt.encode(claims, self._chave_secreta, algorithm=_ALGORITMO)

    def validar(self, token: str) -> UsuarioAutenticado:
        try:
            claims = jwt.decode(
                token,
                self._chave_secreta,
                algorithms=[_ALGORITMO],
                options={
                    "require": _CLAIMS_OBRIGATORIAS,
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
        except jwt.PyJWTError as erro:
            raise TokenInvalido(str(erro)) from erro

        # As datas são conferidas aqui, e não pelo PyJWT, para usar o mesmo relógio da emissão.
        expira_em = claims["exp"]
        if not isinstance(expira_em, int | float) or self._relogio().timestamp() >= expira_em:
            raise TokenInvalido("Token expirado.")

        try:
            return UsuarioAutenticado(
                usuario_id=UUID(claims["sub"]),
                perfil=PerfilUsuario(claims["role"]),
            )
        except (ValueError, TypeError) as erro:
            raise TokenInvalido("Token com dados inválidos.") from erro
