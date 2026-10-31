from dataclasses import dataclass
from datetime import datetime

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada, ValorInvalido
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.value_objects.documento import Documento
from domain.value_objects.numero_os import NumeroOS


@dataclass(frozen=True)
class AcompanhamentoDaOS:
    os: OrdemServico
    estimativa_entrega: datetime | None


class ConsultarOSPublica:
    """O cliente consulta a própria OS pelo número e pelo CPF/CNPJ do titular, sem login (RF-25).

    Número malformado, número inexistente, documento malformado e documento de outro titular
    levantam o mesmo erro, com a mesma mensagem, para a resposta não indicar qual dos dois está
    errado. O cliente é lido mesmo quando excluído logicamente: a OS guarda o histórico dele.
    """

    def __init__(self, ordens: OrdemServicoRepository, clientes: ClienteRepository):
        self._ordens = ordens
        self._clientes = clientes

    async def executar(
        self, numero: str, documento: str, momento_consulta: datetime
    ) -> AcompanhamentoDaOS:
        os = await self._os_do_titular(numero, documento)
        return AcompanhamentoDaOS(os=os, estimativa_entrega=os.estimar_entrega(momento_consulta))

    async def _os_do_titular(self, numero: str, documento: str) -> OrdemServico:
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
