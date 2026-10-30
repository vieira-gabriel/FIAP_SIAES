from application.events.event_dispatcher import EventHandler
from application.handlers.alocacao_pecas_pendentes_handler import AlocacaoPecasPendentesHandler
from domain.events.domain_event import DomainEvent
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class ReservaPecasHandler(EventHandler[OrcamentoFinalizadoEvent]):
    """Reserva as peças da OS que concluiu o orçamento e deixa pendente o que faltar (RF-18).

    O saldo vai primeiro para a OS aberta há mais tempo (RF-19): a OS nova só usa o que sobrar
    depois das OS que já esperam a mesma peça. O handler roda na transação da conclusão, quando
    a OS e os estoques já estão bloqueados, e por isso reserva, grava e deixa a confirmação para
    a unidade de trabalho (RNF-08, RNF-09). A repartição do saldo é a mesma da reposição, feita
    pelo `AlocacaoPecasPendentesHandler`.
    """

    def __init__(self, ordens: OrdemServicoRepository, estoques: EstoqueRepository):
        self._ordens = ordens
        self._alocacao = AlocacaoPecasPendentesHandler(ordens, estoques)

    async def tratar(self, evento: OrcamentoFinalizadoEvent) -> list[DomainEvent]:
        os = await self._ordens.buscar_por_id(evento.os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", evento.os_id)
        pendentes = [item for item in os.pecas if item.quantidade_pendente > 0]
        for item in sorted(pendentes, key=lambda item: item.peca_id):
            await self._alocacao.alocar_saldo(item.peca_id, nova=os)
        return []
