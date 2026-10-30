from uuid import UUID

from application.events.event_dispatcher import EventHandler
from domain.entities.ordem_servico import OrdemServico
from domain.events.domain_event import DomainEvent
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.value_objects.pendencia_peca import PendenciaPeca


class ReservaPecasHandler(EventHandler[OrcamentoFinalizadoEvent]):
    """Reserva as peças da OS que concluiu o orçamento e deixa pendente o que faltar (RF-18).

    O saldo vai primeiro para a OS aberta há mais tempo (RF-19): a OS nova só usa o que sobrar
    depois das OS que já esperam a mesma peça. O handler roda na transação da conclusão, quando
    a OS e os estoques já estão bloqueados, e por isso reserva, grava e deixa a confirmação para
    a unidade de trabalho (RNF-08, RNF-09).
    """

    def __init__(self, ordens: OrdemServicoRepository, estoques: EstoqueRepository):
        self._ordens = ordens
        self._estoques = estoques

    async def tratar(self, evento: OrcamentoFinalizadoEvent) -> list[DomainEvent]:
        os = await self._ordens.buscar_por_id(evento.os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", evento.os_id)
        pendentes = [item for item in os.pecas if item.quantidade_pendente > 0]
        for item in sorted(pendentes, key=lambda item: item.peca_id):
            await self._reservar(os, item.peca_id)
        return []

    async def _reservar(self, os: OrdemServico, peca_id: UUID) -> None:
        estoque = await self._estoques.buscar_por_peca(peca_id)
        if estoque is None:
            return
        alocacoes = estoque.alocar_pendencias(await self._pendencias_da_peca(os, peca_id))
        if not alocacoes:
            return
        await self._estoques.salvar(estoque)
        for alocacao in alocacoes:
            dona = os if alocacao.os_id == os.id else await self._ordens.buscar_por_id(alocacao.os_id)
            dona.alocar_peca(peca_id, alocacao.quantidade_reservada)
            await self._ordens.salvar(dona)

    async def _pendencias_da_peca(self, os: OrdemServico, peca_id: UUID) -> list[PendenciaPeca]:
        """As OS que já esperam a peça vêm antes da nova, para ela perder o empate de data."""
        esperando = [
            outra
            for outra in await self._ordens.listar_pendentes_da_peca(peca_id)
            if outra.id != os.id
        ]
        return [_pendencia(outra, peca_id) for outra in (*esperando, os)]


def _pendencia(os: OrdemServico, peca_id: UUID) -> PendenciaPeca:
    item = next(item for item in os.pecas if item.peca_id == peca_id)
    return PendenciaPeca(os.id, os.data_abertura, item.quantidade_pendente)
