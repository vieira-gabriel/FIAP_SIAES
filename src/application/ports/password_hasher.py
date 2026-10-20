from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Gera e verifica o hash das senhas dos usuários internos (RF-03, RNF-06).

    Os métodos são assíncronos porque o cálculo do hash ocupa a CPU por centenas de
    milissegundos; a implementação o executa fora do loop de eventos (guia, seção 8.1).
    """

    @abstractmethod
    async def gerar_hash(self, senha: str) -> str: ...

    @abstractmethod
    async def verificar(self, senha: str, senha_hash: str) -> bool: ...
