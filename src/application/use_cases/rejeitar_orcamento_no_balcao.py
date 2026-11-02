from uuid import UUID

from application.events.event_dispatcher import EventDispatcher
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class RejeitarOrcamentoNoBalcao:
    """O funcionário registra no balcão a rejeição que o cliente deu pessoalmente (RF-26, RF-18).

    O `OSCanceladaEvent` é despachado na mesma transação, para o estorno das reservas gravar
    junto com o cancelamento (RNF-08). A permissão de Atendente e Gerente é checada na rota.
    """

    def __init__(self, ordens: OrdemServicoRepository, eventos: EventDispatcher):
        self._ordens = ordens
        self._eventos = eventos

    async def executar(self, os_id: UUID, usuario_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        os.rejeitar_orcamento(usuario_id)
        await self._ordens.salvar(os)
        await self._eventos.despachar(os.collect_domain_events())
        return os
