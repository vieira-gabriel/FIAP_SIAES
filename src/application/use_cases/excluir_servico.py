from uuid import UUID

from domain.repositories.servico_repository import ServicoRepository


class ExcluirServico:
    """Exclusão lógica: o serviço sai do catálogo e não entra em novas OS; as OS que já o
    incluem continuam íntegras (RF-11)."""

    def __init__(self, servicos: ServicoRepository):
        self._servicos = servicos

    async def executar(self, id: UUID) -> None:
        servico = await self._servicos.buscar_ativo_por_id(id)
        servico.excluir()
        await self._servicos.salvar(servico)
