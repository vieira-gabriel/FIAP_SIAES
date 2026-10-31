from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository


class ConcluirManutencao:
    """O mecânico atribuído ou o Gerente conclui a manutenção, e a OS passa de `EM_EXECUCAO` para
    `FINALIZADA` com o momento da conclusão gravado (RF-21). Quem pode concluir é regra da
    `OrdemServico`. A partir daí os itens da OS ficam bloqueados."""

    def __init__(self, ordens: OrdemServicoRepository, usuarios: UsuarioRepository):
        self._ordens = ordens
        self._usuarios = usuarios

    async def executar(self, os_id: UUID, usuario_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        usuario = await self._usuarios.buscar_existente_por_id(usuario_id)
        os.concluir_manutencao(usuario)
        await self._ordens.salvar(os)
        return os
