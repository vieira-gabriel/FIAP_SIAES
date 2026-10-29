from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.ordem_servico import OrdemServico
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.value_objects.numero_os import NumeroOS


class PostgresOrdemServicoRepository(OrdemServicoRepository):
    """Provisório até a persistência da OS (issue #88), que cria as tabelas e este adaptador.

    Sem tabela de OS, nenhuma OS tem peça pendente, então a lista vazia é verdadeira e já permite
    à exclusão de peça aplicar a regra do RF-12. Os demais métodos falham para ninguém depender
    deles antes da #88.
    """

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, os: OrdemServico) -> None:
        raise NotImplementedError("persistência da OS pendente (issue #88)")

    async def buscar_por_id(self, id: UUID) -> OrdemServico | None:
        raise NotImplementedError("persistência da OS pendente (issue #88)")

    async def buscar_por_numero(self, numero: NumeroOS) -> OrdemServico | None:
        raise NotImplementedError("persistência da OS pendente (issue #88)")

    async def listar_pendentes_da_peca(self, peca_id: UUID) -> list[OrdemServico]:
        return []
