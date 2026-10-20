from enum import StrEnum


class PerfilUsuario(StrEnum):
    """Perfis de acesso dos usuários internos da oficina (Linguagem Ubíqua §3, RF-02)."""

    ATENDENTE = "ATENDENTE"
    MECANICO = "MECANICO"
    GERENTE = "GERENTE"
