from dataclasses import dataclass

from domain.exceptions import CNPJInvalido
from domain.value_objects.documento import Documento


@dataclass(frozen=True)
class CNPJ(Documento):
    """Documento do cliente pessoa jurídica, com 14 dígitos (RF-05)."""

    TAMANHO = 14
    PESOS_PRIMEIRO_DIGITO = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    PESOS_SEGUNDO_DIGITO = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)

    @staticmethod
    def _erro() -> CNPJInvalido:
        return CNPJInvalido()
