from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from domain.exceptions import ValorInvalido

_CENTAVOS = Decimal("0.01")


@dataclass(frozen=True)
class Valor:
    """Quantia em reais com 2 casas decimais, sem erro de ponto flutuante (RF-17, RNF-11).

    Aceita `Decimal`, `int` ou texto como `"10.50"`. Recusa `float`, porque ele já chega
    impreciso: `0.1 + 0.2` vale `0.30000000000000004`.
    """

    quantia: Decimal

    def __post_init__(self):
        object.__setattr__(self, "quantia", _converter_em_centavos(self.quantia))

    def __add__(self, outro: "Valor") -> "Valor":
        if not isinstance(outro, Valor):
            return NotImplemented
        return Valor(self.quantia + outro.quantia)

    def __mul__(self, quantidade: int) -> "Valor":
        if not _e_inteiro(quantidade):
            return NotImplemented
        return Valor(self.quantia * quantidade)

    __rmul__ = __mul__


def _converter_em_centavos(quantia: object) -> Decimal:
    if isinstance(quantia, float):
        raise TypeError("Use Decimal ou texto para criar um Valor; float é impreciso.")
    if not isinstance(quantia, Decimal | str) and not _e_inteiro(quantia):
        raise TypeError(f"Tipo não suportado para Valor: {type(quantia).__name__}.")
    try:
        decimal = Decimal(quantia)
    except InvalidOperation:
        raise ValorInvalido(f"Valor inválido: {quantia!r}.") from None
    if not decimal.is_finite():
        raise ValorInvalido(f"Valor inválido: {quantia!r}.")
    if decimal < 0:
        raise ValorInvalido(f"O valor não pode ser negativo: {quantia}.")
    return decimal.copy_abs().quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def _e_inteiro(numero: object) -> bool:
    """`bool` é subclasse de `int` em Python, mas `True` não é uma quantidade."""
    return isinstance(numero, int) and not isinstance(numero, bool)
