from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Gera e verifica o hash das senhas dos usuários internos (RF-03, RNF-06)."""

    @abstractmethod
    def gerar_hash(self, senha: str) -> str: ...

    @abstractmethod
    def verificar(self, senha: str, senha_hash: str) -> bool: ...
