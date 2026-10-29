from dataclasses import dataclass
from uuid import UUID

from domain.exceptions import PecaInvalida, QuantidadeInvalida


@dataclass(frozen=True)
class QuantidadePeca:
    """Quantidade de uma peça que um evento manda estornar ou baixar do estoque (RF-18, RF-20)."""

    peca_id: UUID
    quantidade: int

    def __post_init__(self):
        if not isinstance(self.peca_id, UUID):
            raise PecaInvalida("a peça da quantidade é obrigatória")
        if type(self.quantidade) is not int or self.quantidade <= 0:
            raise QuantidadeInvalida("deve ser um número inteiro maior que zero")
