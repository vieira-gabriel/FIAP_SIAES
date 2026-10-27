from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def criar_engine(*, host: str, porta: int, banco: str, usuario: str, senha: str) -> AsyncEngine:
    """Recebe os valores já lidos pelo container, que é quem importa a configuração (guia, 8.1).

    A URL é montada por `URL.create` para que caracteres especiais da senha não a quebrem.
    """
    url = URL.create(
        "postgresql+asyncpg",
        username=usuario,
        password=senha,
        host=host,
        port=porta,
        database=banco,
    )
    return create_async_engine(url)


def criar_fabrica_de_sessoes(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessões com `expire_on_commit=False`: no modo assíncrono, ler um atributo expirado depois
    do commit dispararia um carregamento preguiçoso, que não funciona (guia, 8.1)."""
    return async_sessionmaker(engine, expire_on_commit=False)
