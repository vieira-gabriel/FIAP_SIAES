from datetime import datetime

from application.use_cases.consultar_os_publica import AcompanhamentoDaOS
from application.use_cases.localizar_os_do_titular import LocalizarOSDoTitular
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class AprovarOrcamento:
    """O cliente aprova o orçamento da própria OS, sem login (RF-26).

    Sem peças pendentes a OS aguarda a execução; com elas, aguarda a reposição (RF-19). A transição
    só vale a partir de `AGUARDANDO_APROVACAO` e grava no histórico a origem `CLIENTE`, sem usuário.
    """

    def __init__(self, localizar: LocalizarOSDoTitular, ordens: OrdemServicoRepository):
        self._localizar = localizar
        self._ordens = ordens

    async def executar(
        self, numero: str, documento: str, momento_consulta: datetime
    ) -> AcompanhamentoDaOS:
        os = await self._localizar.executar(numero, documento)
        os.aprovar_orcamento()
        await self._ordens.salvar(os)
        return AcompanhamentoDaOS(os=os, estimativa_entrega=os.estimar_entrega(momento_consulta))
