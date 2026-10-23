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

    valor: Decimal

    def __post_init__(self):
        object.__setattr__(self, "valor", _converter_em_centavos(self.valor))

    def somar(self, outro: "Valor") -> "Valor":
        if not isinstance(outro, Valor):
            raise TypeError(f"Só é possível somar Valor com Valor, não {type(outro).__name__}.")
        return Valor(self.valor + outro.valor)

    def multiplicar(self, quantidade: int) -> "Valor":
        if not _e_inteiro(quantidade):
            raise TypeError(f"A quantidade deve ser inteira, não {type(quantidade).__name__}.")
        return Valor(self.valor * quantidade)


def _converter_em_centavos(valor: object) -> Decimal:
    if isinstance(valor, float):
        raise TypeError("Use Decimal ou texto para criar um Valor; float é impreciso.")
    if not isinstance(valor, Decimal | str) and not _e_inteiro(valor):
        raise TypeError(f"Tipo não suportado para Valor: {type(valor).__name__}.")
    try:
        decimal = Decimal(valor)
    except InvalidOperation:
        raise ValorInvalido(f"Valor inválido: {valor!r}.") from None
    if not decimal.is_finite():
        raise ValorInvalido(f"Valor inválido: {valor!r}.")
    if decimal < 0:
        raise ValorInvalido(f"O valor não pode ser negativo: {valor}.")
    return decimal.copy_abs().quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def _e_inteiro(numero: object) -> bool:
    """`bool` é subclasse de `int` em Python, mas `True` não é uma quantidade."""
    return isinstance(numero, int) and not isinstance(numero, bool)
