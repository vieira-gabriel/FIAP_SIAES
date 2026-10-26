from dataclasses import dataclass

from domain.exceptions import CPFInvalido
from domain.value_objects.documento import Documento


@dataclass(frozen=True)
class CPF(Documento):
    """Documento do cliente pessoa física, com 11 dígitos (RF-05)."""

    TAMANHO = 11
    PESOS_PRIMEIRO_DIGITO = (10, 9, 8, 7, 6, 5, 4, 3, 2)
    PESOS_SEGUNDO_DIGITO = (11, 10, 9, 8, 7, 6, 5, 4, 3, 2)

    @staticmethod
    def _erro() -> CPFInvalido:
        return CPFInvalido()
