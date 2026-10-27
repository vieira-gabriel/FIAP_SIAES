import re
from dataclasses import dataclass
from uuid import UUID

from domain.exceptions import NumeroOSInvalido
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF

_FORMATO = re.compile(r"[0-9]{3}-[0-9A-F]{8}")


@dataclass(frozen=True)
class NumeroOS:
    """Número da OS informado ao cliente, no formato `123-7F3A9C2B` (RF-13).

    Usado junto com o CPF/CNPJ na consulta pública (RF-25). A nova tentativa em caso de
    colisão fica no caso de uso de abertura, que consulta o repositório.
    """

    valor: str

    def __post_init__(self):
        if not _FORMATO.fullmatch(self.valor):
            raise NumeroOSInvalido(self.valor)

    @classmethod
    def gerar(cls, documento: CPF | CNPJ, os_id: UUID) -> "NumeroOS":
        return cls(f"{documento.tres_primeiros_digitos()}-{os_id.hex[:8].upper()}")
