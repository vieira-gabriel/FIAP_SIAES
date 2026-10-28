import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from domain.exceptions import DocumentoInvalido, ValorInvalido

_PONTUACAO = re.compile(r"[.\-/\s]")
_SOMENTE_DIGITOS = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class Documento(ABC):
    """Base de `CPF` e `CNPJ`, que diferem só no tamanho e nos pesos dos dígitos verificadores.

    Guarda apenas os dígitos, sem pontuação, para que o mesmo documento digitado com ou sem
    pontos, traço e barra seja igual (RF-05).
    """

    valor: str

    TAMANHO: ClassVar[int]
    PESOS_PRIMEIRO_DIGITO: ClassVar[tuple[int, ...]]
    PESOS_SEGUNDO_DIGITO: ClassVar[tuple[int, ...]]

    def __post_init__(self):
        digitos = _PONTUACAO.sub("", self.valor)
        if not self._e_valido(digitos):
            raise self._erro()
        object.__setattr__(self, "valor", digitos)

    @staticmethod
    def de_texto(valor: str) -> "Documento":
        """`CPF` com 11 dígitos ou `CNPJ` com 14, ignorando a pontuação (RF-04, RF-05)."""
        # Import local porque cpf.py e cnpj.py importam este módulo.
        from domain.value_objects.cnpj import CNPJ
        from domain.value_objects.cpf import CPF

        quantidade_de_digitos = len(_PONTUACAO.sub("", valor))
        for tipo in (CPF, CNPJ):
            if quantidade_de_digitos == tipo.TAMANHO:
                return tipo(valor)
        raise DocumentoInvalido()

    def tres_primeiros_digitos(self) -> str:
        """Prefixo do número da OS (RF-13)."""
        return self.valor[:3]

    @classmethod
    def _e_valido(cls, digitos: str) -> bool:
        return (
            len(digitos) == cls.TAMANHO
            and _SOMENTE_DIGITOS.fullmatch(digitos) is not None
            and not _todos_iguais(digitos)
            and digitos[-2:] == cls._digitos_verificadores(digitos[:-2])
        )

    @classmethod
    def _digitos_verificadores(cls, base: str) -> str:
        primeiro = _digito_verificador(base, cls.PESOS_PRIMEIRO_DIGITO)
        segundo = _digito_verificador(base + primeiro, cls.PESOS_SEGUNDO_DIGITO)
        return primeiro + segundo

    @staticmethod
    @abstractmethod
    def _erro() -> ValorInvalido: ...


def _digito_verificador(digitos: str, pesos: tuple[int, ...]) -> str:
    """Módulo 11 da Receita Federal, igual para CPF e CNPJ: resto menor que 2 vira 0."""
    resto = sum(int(digito) * peso for digito, peso in zip(digitos, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def _todos_iguais(digitos: str) -> bool:
    """Sequências como 111.111.111-11 passam no módulo 11, mas não são documentos emitidos."""
    return len(set(digitos)) == 1
