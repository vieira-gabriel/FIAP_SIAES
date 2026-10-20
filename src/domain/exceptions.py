class ErroDeDominio(Exception):
    """Base das exceções de regra de negócio, traduzidas para HTTP na camada presentation."""


class UsuarioInvalido(ErroDeDominio):
    def __init__(self, motivo: str):
        super().__init__(f"Usuário inválido: {motivo}")
        self.motivo = motivo


class CredenciaisInvalidas(ErroDeDominio):
    """E-mail inexistente, senha incorreta ou usuário desativado (RF-01).

    A mensagem é a mesma nos três casos para não revelar quais e-mails estão cadastrados.
    """

    def __init__(self):
        super().__init__("E-mail ou senha inválidos.")
