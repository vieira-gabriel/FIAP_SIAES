from uuid import UUID

from application.events.event_dispatcher import EventDispatcher
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.peca_repository import PecaRepository
from domain.repositories.servico_repository import ServicoRepository


class FinalizarOrcamento:
    """Congela os valores vigentes do catálogo e envia o orçamento ao cliente (RF-17).

    O `OrcamentoFinalizadoEvent` é despachado na mesma transação, para a reserva das peças (RF-18,
    issue #93) gravar junto com a conclusão (RNF-08).
    """

    def __init__(
        self,
        ordens: OrdemServicoRepository,
        estoques: EstoqueRepository,
        servicos: ServicoRepository,
        pecas: PecaRepository,
        eventos: EventDispatcher,
    ):
        self._ordens = ordens
        self._estoques = estoques
        self._servicos = servicos
        self._pecas = pecas
        self._eventos = eventos

    async def executar(self, os_id: UUID, usuario_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        # `ExcluirPeca` bloqueia o mesmo estoque antes de conferir as pendências. Bloqueá-lo antes
        # de ler o catálogo impede que a peça seja excluída entre a leitura e a gravação da
        # pendência (RF-12). A ordem pelo id evita o impasse entre duas conclusões simultâneas.
        for item in sorted(os.pecas, key=lambda item: item.peca_id):
            await self._estoques.buscar_por_peca(item.peca_id)
        servicos = [await self._servicos.buscar_por_id(item.servico_id) for item in os.servicos]
        pecas = [await self._pecas.buscar_por_id(item.peca_id) for item in os.pecas]
        os.finalizar_orcamento(
            usuario_id,
            [servico for servico in servicos if servico is not None],
            [peca for peca in pecas if peca is not None],
        )
        await self._ordens.salvar(os)
        await self._eventos.despachar(os.collect_domain_events())
        return os
