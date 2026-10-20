from enum import StrEnum


class OrigemTransicao(StrEnum):
    """Quem provocou uma transição de status, registrado no histórico (RF-24)."""

    USUARIO = "USUARIO"
    CLIENTE = "CLIENTE"
    SISTEMA = "SISTEMA"
