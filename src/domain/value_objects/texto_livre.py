from collections.abc import Callable

from domain.exceptions import ValorInvalido


def exigir_sem_marcacao(erro: Callable[[str], ValorInvalido], **campos: str) -> None:
    """Recusa o texto livre com `<`, para nenhum campo guardar marcação HTML (RNF-04).

    O texto é recusado, e não escapado: o banco e o histórico guardam o que o usuário digitou.
    """
    for nome, texto in campos.items():
        if "<" in texto:
            raise erro(f"o campo '{nome}' não pode conter o caractere '<'")
