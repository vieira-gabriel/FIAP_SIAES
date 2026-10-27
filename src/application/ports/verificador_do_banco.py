from abc import ABC, abstractmethod


class VerificadorDoBanco(ABC):
    """Informa se o banco de dados responde, para o health check (RNF-16)."""

    @abstractmethod
    async def esta_disponivel(self) -> bool: ...
