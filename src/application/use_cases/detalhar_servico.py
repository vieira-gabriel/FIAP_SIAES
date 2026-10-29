from uuid import UUID

from domain.entities.servico import Servico
from domain.repositories.servico_repository import ServicoRepository


class DetalharServico:
    """Consulta de um serviço ativo do catálogo (RF-10)."""

    def __init__(self, servicos: ServicoRepository):
        self._servicos = servicos

    async def executar(self, id: UUID) -> Servico:
        return await self._servicos.buscar_ativo_por_id(id)
