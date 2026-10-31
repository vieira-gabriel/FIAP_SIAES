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


class DocumentoInvalido(ValorInvalido):
    """Quantidade de dígitos que não é de CPF nem de CNPJ."""

    def __init__(self):
        super().__init__("Documento inválido: informe um CPF (11 dígitos) ou um CNPJ (14 dígitos).")


class PlacaInvalida(ValorInvalido):
    def __init__(self, placa: str):
        super().__init__(
            f"Placa inválida: {placa!r}. Use o padrão antigo (ABC1234) ou Mercosul (ABC1D23)."
        )
        self.placa = placa


class NumeroOSInvalido(ValorInvalido):
    def __init__(self, numero: str):
        super().__init__(f"Número da OS inválido: {numero!r}. Use o formato 123-7F3A9C2B.")
        self.numero = numero


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


class ClienteInvalido(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Cliente inválido: {motivo}")
        self.motivo = motivo


class VeiculoInvalido(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Veículo inválido: {motivo}")
        self.motivo = motivo


class OrdemServicoInvalida(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Ordem de serviço inválida: {motivo}")
        self.motivo = motivo


class QuantidadeInvalida(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Quantidade inválida: {motivo}")
        self.motivo = motivo


class AlocacaoInvalida(ValorInvalido):
    def __init__(self, motivo: str):
        super().__init__(f"Alocação de peça inválida: {motivo}")
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


class QuantidadeFisicaAbaixoDaReservada(RegraDeNegocioViolada):
    """O ajuste não pode deixar a quantidade física abaixo da reservada às OS (RF-12)."""

    def __init__(self, nova_quantidade_fisica: int, quantidade_reservada: int):
        super().__init__(
            f"A quantidade física ({nova_quantidade_fisica}) não pode ficar abaixo da quantidade "
            f"reservada ({quantidade_reservada})."
        )
        self.nova_quantidade_fisica = nova_quantidade_fisica
        self.quantidade_reservada = quantidade_reservada


class ItensBloqueados(RegraDeNegocioViolada):
    """Alteração de serviços ou peças em um status que não a permite, como `FINALIZADA` (RF-21)."""

    def __init__(self, status_atual: StatusOS):
        super().__init__(f"Os itens da OS não podem ser alterados no status {status_atual.value}.")
        self.status_atual = status_atual


class ItemIndisponivel(RegraDeNegocioViolada):
    """Serviço ou peça excluído do catálogo não entra em novas OS (RF-11, RF-12, RF-17)."""

    def __init__(self, nome: str):
        super().__init__(f"O item {nome!r} está inativo no catálogo e não pode entrar na OS.")
        self.nome = nome


class ItemJaIncluido(RegraDeNegocioViolada):
    def __init__(self, nome: str):
        super().__init__(f"O item {nome!r} já está na OS.")
        self.nome = nome


class EmailJaCadastrado(RegraDeNegocioViolada):
    """O e-mail é o login, então identifica um único usuário (RF-01, RF-03)."""

    def __init__(self):
        super().__init__("Já existe um usuário cadastrado com este e-mail.")


class AlteracaoDoProprioAcesso(RegraDeNegocioViolada):
    """O Gerente não desativa nem muda o próprio perfil: a oficina ficaria sem Gerente (RF-03)."""

    def __init__(self, acao: str):
        super().__init__(f"O Gerente não pode {acao}; peça a outro Gerente.")
        self.acao = acao


class CodigoDeServicoJaCadastrado(RegraDeNegocioViolada):
    """O código identifica um único serviço do catálogo, mesmo excluído (RF-10, RF-11)."""

    def __init__(self, codigo: str):
        super().__init__(f"Já existe um serviço com o código {codigo!r}.")
        self.codigo = codigo


class DocumentoJaCadastrado(RegraDeNegocioViolada):
    """Um documento identifica um único cliente, mesmo excluído logicamente (RF-04, RF-06).

    Sem o número na mensagem, como em `CPFInvalido` (RNF-04).
    """

    def __init__(self):
        super().__init__("Já existe um cliente cadastrado com este documento.")


class CodigoDePecaJaCadastrado(RegraDeNegocioViolada):
    """O código de referência identifica uma única peça, mesmo excluída (RF-12)."""

    def __init__(self, codigo_referencia: str):
        super().__init__(f"Já existe uma peça com o código de referência {codigo_referencia!r}.")
        self.codigo_referencia = codigo_referencia


class NumeroOSJaCadastrado(RegraDeNegocioViolada):
    """O número identifica uma única OS na consulta pública (RF-13, RF-25)."""

    def __init__(self, numero: str):
        super().__init__(f"Já existe uma OS com o número {numero}.")
        self.numero = numero


class PecaComPendencia(RegraDeNegocioViolada):
    """Peça que alguma OS ainda espera não pode ser excluída (RF-12)."""

    def __init__(self, peca: str, numeros_das_os: list[str]):
        super().__init__(
            f"A peça {peca!r} está pendente nas OS {', '.join(numeros_das_os)} e não pode ser "
            "excluída."
        )
        self.peca = peca
        self.numeros_das_os = numeros_das_os


class NumeroOSIndisponivel(RegraDeNegocioViolada):
    """Nenhum número livre foi gerado após as tentativas da abertura (RF-13)."""

    def __init__(self):
        super().__init__("Não foi possível gerar um número livre para a OS. Tente novamente.")


class MecanicoIndisponivel(RegraDeNegocioViolada):
    """O usuário indicado não tem o perfil Mecânico ou está desativado (RF-16)."""

    def __init__(self):
        super().__init__("O usuário indicado não é um mecânico ativo.")


class OSDeOutroCliente(RegraDeNegocioViolada):
    """A placa informada pertence a um veículo de outro cliente (RF-07, RF-13)."""

    def __init__(self):
        super().__init__("A placa informada pertence a um veículo de outro cliente.")


class PlacaJaCadastrada(RegraDeNegocioViolada):
    """A placa identifica um único veículo ativo; a de um excluído pode ser recadastrada (RF-07)."""

    def __init__(self):
        super().__init__("Já existe um veículo ativo cadastrado com esta placa.")


class PecasPendentes(RegraDeNegocioViolada):
    """A OS só sai de `AGUARDANDO_PECA` quando todas as peças estão reservadas (RF-19)."""

    def __init__(self, pecas: list[str]):
        super().__init__(f"A OS ainda tem peças pendentes: {', '.join(pecas)}.")
        self.pecas = pecas


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


class AcessoNegado(ErroDeDominio):
    """O usuário não pode executar a operação, como iniciar a execução de uma OS alheia (RF-20).

    Não herda das bases de 400/404/422 porque a camada presentation a traduz para 403.
    """

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo
