from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class EntregarVeiculo:
    """O atendente entrega o veículo ao cliente, e a OS passa de `FINALIZADA` para `ENTREGUE`,
    estado final (RF-22). A permissão de Atendente e Gerente é checada na rota."""

    def __init__(self, ordens: OrdemServicoRepository):
        self._ordens = ordens

    async def executar(self, os_id: UUID, usuario_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        os.entregar_veiculo(usuario_id)
        await self._ordens.salvar(os)
        return os
