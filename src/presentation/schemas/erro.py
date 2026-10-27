from pydantic import BaseModel, Field


class DetalheDoErro(BaseModel):
    campo: str = Field(examples=["body.email"])
    mensagem: str = Field(examples=["Field required"])


class ErroResponse(BaseModel):
    """Formato único de todas as respostas de erro da API (issue #30)."""

    codigo: str = Field(examples=["VALOR_INVALIDO"])
    mensagem: str = Field(examples=["CPF inválido."])
    detalhes: list[DetalheDoErro] = Field(default_factory=list)
