"""Limite de requisições por IP nas rotas públicas, contra força bruta e raspagem (RNF-05).

Todas as rotas públicas dividem o mesmo contador por IP. Uso em uma rota pública, que precisa
receber o `request: Request`:

    @router.post("")
    @limite_publico
    async def consultar(request: Request, ...): ...

O contador fica em memória, o que basta para a instância única do MVP. O limite vem de
`RATE_LIMIT_PUBLICO`, lido pelo container na subida (`configurar_limite_publico`).
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from limits import parse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from presentation.schemas.erro import ErroResponse

limiter = Limiter(key_func=get_remote_address)

_limite_publico: str | None = None


def configurar_limite_publico(limite: str) -> None:
    """Recusa o limite malformado na subida e zera os contadores."""
    global _limite_publico
    parse(limite)
    _limite_publico = limite
    limiter.reset()


def _limite_configurado() -> str:
    if _limite_publico is None:
        raise RuntimeError("O limite das rotas públicas só existe depois da subida da aplicação.")
    return _limite_publico


# Um só contador para todas as rotas públicas: quem alterna entre a consulta e a aprovação não
# ganha mais tentativas de adivinhar o CPF/CNPJ.
limite_publico = limiter.shared_limit(_limite_configurado, scope="publico")


async def tratar_limite_excedido(_request: Request, erro: RateLimitExceeded) -> JSONResponse:
    corpo = ErroResponse(
        codigo="LIMITE_DE_REQUISICOES_EXCEDIDO",
        mensagem="Muitas requisições. Tente novamente em instantes.",
    )
    segundos = erro.limit.limit.get_expiry()
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=corpo.model_dump(),
        headers={"Retry-After": str(segundos)},
    )
