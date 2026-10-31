from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada, ValorInvalido
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.value_objects.documento import Documento
from domain.value_objects.numero_os import NumeroOS


class LocalizarOSDoTitular:
    """Identifica o cliente nas rotas públicas: o número da OS junto com o CPF/CNPJ do titular
    (RF-25, RF-26).

    Número malformado, número inexistente, documento malformado e documento de outro titular
    levantam o mesmo erro, com a mesma mensagem, para a resposta não indicar qual dos dois está
    errado. O cliente é lido mesmo quando excluído logicamente: a OS guarda o histórico dele.
    A OS volta bloqueada (`buscar_por_numero`), pronta para quem for alterá-la.
    """

    def __init__(self, ordens: OrdemServicoRepository, clientes: ClienteRepository):
        self._ordens = ordens
        self._clientes = clientes

    async def executar(self, numero: str, documento: str) -> OrdemServico:
        try:
            numero_os = NumeroOS(numero.strip().upper())
            titular = Documento.de_texto(documento)
        except ValorInvalido:
            raise _nao_encontrada() from None
        os = await self._ordens.buscar_por_numero(numero_os)
        if os is None:
            raise _nao_encontrada()
        cliente = await self._clientes.buscar_por_id(os.cliente_id)
        if cliente is None or cliente.documento != titular:
            raise _nao_encontrada()
        return os


def _nao_encontrada() -> EntidadeNaoEncontrada:
    return EntidadeNaoEncontrada("Ordem de serviço", "com o número e o documento informados")
