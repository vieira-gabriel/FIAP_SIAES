from uuid import UUID

from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.peca_repository import PecaRepository


class ExcluirPeca:
    """Exclusão lógica: a peça sai do cadastro e não entra em novas OS; as reservas e as OS
    existentes continuam íntegras (RF-12)."""

    def __init__(self, pecas: PecaRepository, ordens: OrdemServicoRepository):
        self._pecas = pecas
        self._ordens = ordens

    async def executar(self, id: UUID) -> None:
        peca = await self._pecas.buscar_ativa_por_id(id)
        pendentes = await self._ordens.listar_pendentes_da_peca(peca.id)
        peca.excluir([os.numero for os in pendentes])
        await self._pecas.salvar(peca)
