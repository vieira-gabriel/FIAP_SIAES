from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.servico_repository import ServicoRepository


class IncluirServicoNaOS:
    """Inclui um serviço do catálogo na OS durante o diagnóstico (RF-17).

    Só serviço ativo e ainda fora da OS entra, e só em `EM_DIAGNOSTICO`; as regras ficam na
    `OrdemServico`.
    """

    def __init__(self, ordens: OrdemServicoRepository, servicos: ServicoRepository):
        self._ordens = ordens
        self._servicos = servicos

    async def executar(self, os_id: UUID, servico_id: UUID) -> OrdemServico:
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        servico = await self._servicos.buscar_por_id(servico_id)
        if servico is None:
            raise EntidadeNaoEncontrada("Serviço", servico_id)
        os.incluir_servico(servico)
        await self._ordens.salvar(os)
        return os
