from uuid import UUID

from domain.repositories.veiculo_repository import VeiculoRepository


class ExcluirVeiculo:
    """Exclusão lógica: o veículo sai do cadastro e as OS dele são preservadas (RF-09)."""

    def __init__(self, veiculos: VeiculoRepository):
        self._veiculos = veiculos

    async def executar(self, id: UUID) -> None:
        veiculo = await self._veiculos.buscar_ativo_por_id(id)
        veiculo.excluir()
        await self._veiculos.salvar(veiculo)
