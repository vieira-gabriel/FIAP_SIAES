from dataclasses import dataclass, field

from domain.value_objects.valor import Valor


@dataclass(frozen=True)
class Orcamento:
    """Valor cotado ao cliente, somado a partir dos valores congelados nos itens (RF-17, RNF-11).

    O `total` é calculado na criação a partir dos subtotais, e não é informado de fora.
    """

    subtotal_servicos: Valor
    subtotal_pecas: Valor
    total: Valor = field(init=False)

    def __post_init__(self):
        for subtotal in (self.subtotal_servicos, self.subtotal_pecas):
            if not isinstance(subtotal, Valor):
                raise TypeError(
                    f"Os subtotais do Orcamento devem ser Valor, não {type(subtotal).__name__}."
                )
        object.__setattr__(self, "total", self.subtotal_servicos.somar(self.subtotal_pecas))
