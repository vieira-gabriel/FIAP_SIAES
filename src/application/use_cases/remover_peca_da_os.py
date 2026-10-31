from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class RemoverPecaDaOS:
    """Tira uma peça da OS durante o diagnóstico (RF-17)."""

    def __init__(self, ordens: OrdemServicoRepository):
        self._ordens = ordens

    async def executar(self, os_id: UUID, peca_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        os.remover_peca(peca_id)
        await self._ordens.salvar(os)
        return os
