from domain.entities.servico import Servico
from domain.repositories.servico_repository import ServicoRepository


class ListarServicos:
    """Catálogo de serviços ativos, em ordem de nome; os excluídos ficam fora (RF-10)."""

    def __init__(self, servicos: ServicoRepository):
        self._servicos = servicos

    async def executar(self) -> list[Servico]:
        return await self._servicos.listar()
