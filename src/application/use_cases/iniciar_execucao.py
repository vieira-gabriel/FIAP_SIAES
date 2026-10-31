from uuid import UUID

from application.events.event_dispatcher import EventDispatcher
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository


class IniciarExecucao:
    """O mecânico atribuído ou o Gerente inicia a execução da OS (RF-20).

    A OS decide quem pode iniciar. O `ExecucaoIniciadaEvent` é despachado na mesma transação, para
    a baixa das peças gravar junto com a mudança de status e o início da execução (RNF-08).
    """

    def __init__(
        self,
        ordens: OrdemServicoRepository,
        usuarios: UsuarioRepository,
        eventos: EventDispatcher,
    ):
        self._ordens = ordens
        self._usuarios = usuarios
        self._eventos = eventos

    async def executar(self, os_id: UUID, usuario_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        usuario = await self._usuarios.buscar_existente_por_id(usuario_id)
        os.iniciar_execucao(usuario)
        await self._ordens.salvar(os)
        await self._eventos.despachar(os.collect_domain_events())
        return os
