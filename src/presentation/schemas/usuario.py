from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario

# O bcrypt considera no máximo 72 bytes; acentos ocupam mais de um byte em UTF-8.
_LIMITE_BYTES_BCRYPT = 72


def _caber_no_bcrypt(senha: str) -> str:
    if len(senha.encode("utf-8")) > _LIMITE_BYTES_BCRYPT:
        raise ValueError(f"a senha não pode passar de {_LIMITE_BYTES_BCRYPT} bytes")
    return senha


Senha = Annotated[
    str,
    Field(min_length=8, examples=["senha-forte-123"]),
    AfterValidator(_caber_no_bcrypt),
]


class UsuarioCadastroRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=200, examples=["Ana Atendente"])
    email: str = Field(min_length=3, max_length=254, examples=["ana@oficina.com"])
    senha: Senha
    perfil: PerfilUsuario


class UsuarioAtualizacaoRequest(BaseModel):
    """A senha muda só pela rota própria, `PUT /usuarios/{id}/senha`."""

    nome: str = Field(min_length=1, max_length=200, examples=["Ana Atendente"])
    email: str = Field(min_length=3, max_length=254, examples=["ana@oficina.com"])
    perfil: PerfilUsuario


class SenhaRequest(BaseModel):
    senha: Senha


class UsuarioResponse(BaseModel):
    """Sem o hash da senha (RNF-06)."""

    id: UUID
    nome: str
    email: str
    perfil: PerfilUsuario
    ativo: bool

    @classmethod
    def de_entidade(cls, usuario: Usuario) -> "UsuarioResponse":
        return cls(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            perfil=usuario.perfil,
            ativo=usuario.ativo,
        )
