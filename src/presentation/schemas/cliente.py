from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from domain.entities.cliente import Cliente


class ClienteRequest(BaseModel):
    """O documento pode vir com ou sem pontuação: 11 dígitos são CPF e 14 são CNPJ (RF-04)."""

    nome: str = Field(min_length=1, max_length=200, examples=["Maria Silva"])
    documento: str = Field(min_length=1, max_length=20, examples=["529.982.247-25"])
    email: str = Field(min_length=3, max_length=254, examples=["maria@exemplo.com"])
    telefone: str = Field(min_length=1, max_length=30, examples=["(11) 98765-4321"])


class ClienteResponse(BaseModel):
    id: UUID
    nome: str
    documento: str = Field(examples=["52998224725"])
    tipo_documento: Literal["CPF", "CNPJ"]
    email: str
    telefone: str

    @classmethod
    def de_entidade(cls, cliente: Cliente) -> "ClienteResponse":
        return cls(
            id=cliente.id,
            nome=cliente.nome,
            documento=cliente.documento.valor,
            tipo_documento=type(cliente.documento).__name__,
            email=cliente.email,
            telefone=cliente.telefone,
        )
