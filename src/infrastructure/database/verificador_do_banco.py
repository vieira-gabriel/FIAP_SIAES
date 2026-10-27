import asyncio

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from application.ports.verificador_do_banco import VerificadorDoBanco


class VerificadorDoBancoSqlAlchemy(VerificadorDoBanco):
    """Executa `SELECT 1`. O tempo limite impede que um banco travado prenda o health check."""

    def __init__(self, engine: AsyncEngine, tempo_limite_segundos: float = 2.0):
        self._engine = engine
        self._tempo_limite_segundos = tempo_limite_segundos

    async def esta_disponivel(self) -> bool:
        try:
            async with asyncio.timeout(self._tempo_limite_segundos):
                async with self._engine.connect() as conexao:
                    await conexao.execute(text("SELECT 1"))
        except (OSError, TimeoutError, SQLAlchemyError):
            return False
        return True
