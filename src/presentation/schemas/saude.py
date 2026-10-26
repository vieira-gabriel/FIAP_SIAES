from typing import Literal

from pydantic import BaseModel


class SaudeResponse(BaseModel):
    status: Literal["online", "indisponivel"]
    banco: Literal["disponivel", "indisponivel"]
    message: str
