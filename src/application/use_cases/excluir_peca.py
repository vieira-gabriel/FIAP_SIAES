from uuid import UUID

from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.peca_repository import PecaRepository


class ExcluirPeca:
    """Exclusão lógica: a peça sai do cadastro e não entra em novas OS; as reservas e as OS
    existentes continuam íntegras (RF-12)."""

    def __init__(
        self,
        pecas: PecaRepository,
        estoques: EstoqueRepository,
        ordens: OrdemServicoRepository,
    ):
        self._pecas = pecas
        self._estoques = estoques
        self._ordens = ordens

    async def executar(self, id: UUID) -> None:
        peca = await self._pecas.buscar_ativa_por_id(id)
        # A conclusão do orçamento bloqueia o mesmo estoque ao reservar; bloqueá-lo aqui impede
        # que uma pendência nova surja entre a consulta abaixo e a exclusão (RNF-09).
        await self._estoques.buscar_por_peca(peca.id)
        pendentes = await self._ordens.listar_pendentes_da_peca(peca.id)
        peca.excluir([os.numero for os in pendentes])
        await self._pecas.salvar(peca)
