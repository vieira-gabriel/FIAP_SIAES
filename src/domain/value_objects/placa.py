import re
from dataclasses import dataclass

from domain.exceptions import PlacaInvalida

_PADRAO_ANTIGO = re.compile(r"[A-Z]{3}[0-9]{4}")
_PADRAO_MERCOSUL = re.compile(r"[A-Z]{3}[0-9][A-Z][0-9]{2}")
_SEPARADORES = re.compile(r"[-\s]")


@dataclass(frozen=True)
class Placa:
    """Placa no padrão antigo (`ABC1234`) ou Mercosul (`ABC1D23`) (RF-08).

    Aceita minúsculas, hífen e espaços e guarda o valor normalizado, para que a mesma placa
    digitada de formas diferentes seja igual.
    """

    valor: str

    def __post_init__(self):
        normalizada = _SEPARADORES.sub("", self.valor).upper()
        if not (_PADRAO_ANTIGO.fullmatch(normalizada) or _PADRAO_MERCOSUL.fullmatch(normalizada)):
            raise PlacaInvalida(self.valor)
        object.__setattr__(self, "valor", normalizada)
