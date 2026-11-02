from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class AprovarOrcamentoNoBalcao:
    """O funcionário registra no balcão a aprovação que o cliente deu pessoalmente (RF-26).

    A transição é a mesma da rota pública, mas o histórico grava o funcionário (RF-24). A
    permissão de Atendente e Gerente é checada na rota.
    """

    def __init__(self, ordens: OrdemServicoRepository):
        self._ordens = ordens

    async def executar(self, os_id: UUID, usuario_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        os.aprovar_orcamento(usuario_id)
        await self._ordens.salvar(os)
        return os
