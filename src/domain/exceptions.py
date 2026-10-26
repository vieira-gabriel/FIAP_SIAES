from domain.value_objects.status_os import StatusOS


class ErroDeDominio(Exception):
    """Base das exceções de regra de negócio, traduzidas para HTTP na camada presentation."""


class EntidadeNaoEncontrada(ErroDeDominio):
    def __init__(self, entidade: str, identificador: object):
        super().__init__(f"{entidade} não encontrado(a): {identificador}.")
        self.entidade = entidade
        self.identificador = identificador


class RegraDeNegocioViolada(ErroDeDominio):
    pass


class ValorInvalido(ErroDeDominio):
    pass


class CPFInvalido(ValorInvalido):
    """Sem o número na mensagem para não expor dado pessoal em respostas e logs (RNF-04)."""

    def __init__(self):
        super().__init__("CPF inválido.")


class CNPJInvalido(ValorInvalido):
    def __init__(self):
        super().__init__("CNPJ inválido.")


class PlacaInvalida(ValorInvalido):
    def __init__(self, placa: str):
        super().__init__(
            f"Placa inválida: {placa!r}. Use o padrão antigo (ABC1234) ou Mercosul (ABC1D23)."
        )
        self.placa = placa


class ServicoInvalido(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Serviço inválido: {motivo}")
        self.motivo = motivo


class PecaInvalida(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Peça inválida: {motivo}")
        self.motivo = motivo


class UsuarioInvalido(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Usuário inválido: {motivo}")
        self.motivo = motivo


class TransicaoDeStatusInvalida(RegraDeNegocioViolada):
    def __init__(self, status_atual: StatusOS, status_pretendido: StatusOS):
        super().__init__(
            f"Transição de status inválida: {status_atual.value} → {status_pretendido.value}."
        )
        self.status_atual = status_atual
        self.status_pretendido = status_pretendido


class SaldoInsuficiente(RegraDeNegocioViolada):
    """O saldo disponível de uma peça nunca fica negativo (RF-12)."""

    def __init__(self, peca: str, quantidade_solicitada: int, saldo_disponivel: int):
        super().__init__(
            f"Saldo insuficiente da peça {peca}: solicitado {quantidade_solicitada}, "
            f"disponível {saldo_disponivel}."
        )
        self.peca = peca
        self.quantidade_solicitada = quantidade_solicitada
        self.saldo_disponivel = saldo_disponivel


class ItensBloqueados(RegraDeNegocioViolada):
    """Alteração de serviços ou peças em um status que não a permite, como `FINALIZADA` (RF-21)."""

    def __init__(self, status_atual: StatusOS):
        super().__init__(f"Os itens da OS não podem ser alterados no status {status_atual.value}.")
        self.status_atual = status_atual


class MotivoObrigatorio(RegraDeNegocioViolada):
    """O cancelamento da OS exige motivo, registrado no histórico (RF-23, RF-24)."""

    def __init__(self):
        super().__init__("Informe o motivo do cancelamento.")


class CredenciaisInvalidas(ErroDeDominio):
    """E-mail inexistente, senha incorreta ou usuário desativado (RF-01).

    A mensagem é a mesma nos três casos para não revelar quais e-mails estão cadastrados.
    Não herda das bases de 400/404/422 porque a rota de login a traduz para 401.
    """

    def __init__(self):
        super().__init__("E-mail ou senha inválidos.")
