from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario


class TokenInvalido(Exception):
    """Token ausente de dados obrigatórios, com assinatura inválida ou expirado (RNF-03)."""


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Dados do usuário extraídos de um token válido."""

    usuario_id: UUID
    perfil: PerfilUsuario


class TokenService(ABC):
    """Emite e valida os tokens de acesso dos usuários internos (RF-01)."""

    @abstractmethod
    def emitir(self, usuario: Usuario) -> str: ...

    @abstractmethod
    def validar(self, token: str) -> UsuarioAutenticado:
        """Devolve os dados do token ou lança `TokenInvalido`."""
