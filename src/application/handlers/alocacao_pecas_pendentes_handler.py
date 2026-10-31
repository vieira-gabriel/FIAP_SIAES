from uuid import UUID

from application.events.event_dispatcher import EventHandler
from domain.entities.ordem_servico import OrdemServico
from domain.events.domain_event import DomainEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.value_objects.pendencia_peca import PendenciaPeca


class AlocacaoPecasPendentesHandler(EventHandler[SaldoPecaAtualizadoEvent]):
    """Aloca o saldo de uma peça às OS que esperam por ela e libera as que ficam completas (RF-19).

    O saldo vai primeiro para a OS aberta há mais tempo, e uma OS em `AGUARDANDO_PECA` que fica
    sem pendência passa a `AGUARDANDO_EXECUCAO`. O handler usa o saldo atual do estoque, e não o
    do evento, porque duas operações na mesma transação geram dois eventos e o primeiro chega com
    um saldo já antigo. Roda na transação da operação que aumentou o saldo, com o estoque já
    bloqueado, e deixa a confirmação para a unidade de trabalho (RNF-08, RNF-09).
    """

    def __init__(self, ordens: OrdemServicoRepository, estoques: EstoqueRepository):
        self._ordens = ordens
        self._estoques = estoques

    async def tratar(self, evento: SaldoPecaAtualizadoEvent) -> list[DomainEvent]:
        await self.alocar_saldo(evento.peca_id)
        return []

    async def alocar_saldo(self, peca_id: UUID, nova: OrdemServico | None = None) -> None:
        """Reparte o saldo da peça pelas OS pendentes, da mais antiga para a mais nova.

        A OS `nova`, que acabou de concluir o orçamento, já vem carregada e entra por último entre
        as pendências, para perder o empate de data de abertura para quem já esperava a peça.
        """
        estoque = await self._estoques.buscar_por_peca(peca_id)
        if estoque is None:
            return
        alocacoes = estoque.alocar_pendencias(await self._pendencias_da_peca(peca_id, nova))
        if not alocacoes:
            return
        await self._estoques.salvar(estoque)
        for alocacao in alocacoes:
            if nova is not None and alocacao.os_id == nova.id:
                dona = nova
            else:
                dona = await self._ordens.buscar_por_id(alocacao.os_id)
            dona.alocar_peca(peca_id, alocacao.quantidade_reservada)
            await self._ordens.salvar(dona)

    async def _pendencias_da_peca(
        self, peca_id: UUID, nova: OrdemServico | None
    ) -> list[PendenciaPeca]:
        esperando = await self._ordens.listar_pendentes_da_peca(peca_id)
        if nova is None:
            return [_pendencia(os, peca_id) for os in esperando]
        antigas = [os for os in esperando if os.id != nova.id]
        return [_pendencia(os, peca_id) for os in (*antigas, nova)]


def _pendencia(os: OrdemServico, peca_id: UUID) -> PendenciaPeca:
    item = next(item for item in os.pecas if item.peca_id == peca_id)
    return PendenciaPeca(os.id, os.data_abertura, item.quantidade_pendente)
