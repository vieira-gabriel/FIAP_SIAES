from dataclasses import dataclass
from uuid import UUID

from domain.exceptions import AlocacaoInvalida, QuantidadeInvalida


@dataclass(frozen=True)
class AlocacaoPeca:
    """Quantidade de uma peça reservada para uma OS que a esperava (RF-18, RF-19)."""

    os_id: UUID
    quantidade_reservada: int

    def __post_init__(self):
        if not isinstance(self.os_id, UUID):
            raise AlocacaoInvalida("a OS da alocação é obrigatória")
        if type(self.quantidade_reservada) is not int or self.quantidade_reservada <= 0:
            raise QuantidadeInvalida("deve ser um número inteiro maior que zero")
