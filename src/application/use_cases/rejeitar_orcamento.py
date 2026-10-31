from datetime import datetime

from application.events.event_dispatcher import EventDispatcher
from application.use_cases.consultar_os_publica import AcompanhamentoDaOS
from application.use_cases.localizar_os_do_titular import LocalizarOSDoTitular
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class RejeitarOrcamento:
    """O cliente rejeita o orçamento da própria OS, sem login, e a OS é cancelada (RF-26).

    A transição só vale a partir de `AGUARDANDO_APROVACAO` e grava no histórico a origem `CLIENTE`,
    sem usuário. O `OSCanceladaEvent` é despachado na mesma transação, para o estorno das reservas
    gravar junto com o cancelamento (RF-18, RNF-08), pelo mesmo handler do cancelamento do Gerente.
    """

    def __init__(
        self,
        localizar: LocalizarOSDoTitular,
        ordens: OrdemServicoRepository,
        eventos: EventDispatcher,
    ):
        self._localizar = localizar
        self._ordens = ordens
        self._eventos = eventos

    async def executar(
        self, numero: str, documento: str, momento_consulta: datetime
    ) -> AcompanhamentoDaOS:
        os = await self._localizar.executar(numero, documento)
        os.rejeitar_orcamento()
        await self._ordens.salvar(os)
        await self._eventos.despachar(os.collect_domain_events())
        return AcompanhamentoDaOS(os=os, estimativa_entrega=os.estimar_entrega(momento_consulta))
