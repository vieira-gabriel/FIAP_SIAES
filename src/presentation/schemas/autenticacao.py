from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, examples=["admin@oficina.com"])
    senha: str = Field(min_length=1, max_length=128, examples=["senha-forte-123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
