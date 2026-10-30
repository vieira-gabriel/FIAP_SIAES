from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.peca_repository import PecaRepository


class IncluirPecaNaOS:
    """Inclui uma peça do catálogo na OS durante o diagnóstico, com a quantidade (RF-17).

    Só peça ativa e ainda fora da OS entra, com quantidade inteira maior que zero, e só em
    `EM_DIAGNOSTICO`; as regras ficam na `OrdemServico`. A reserva no estoque só acontece na
    conclusão do orçamento (RF-18).
    """

    def __init__(self, ordens: OrdemServicoRepository, pecas: PecaRepository):
        self._ordens = ordens
        self._pecas = pecas

    async def executar(self, os_id: UUID, peca_id: UUID, quantidade: int) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        peca = await self._pecas.buscar_por_id(peca_id)
        if peca is None:
            raise EntidadeNaoEncontrada("Peça", peca_id)
        os.incluir_peca(peca, quantidade)
        await self._ordens.salvar(os)
        return os
