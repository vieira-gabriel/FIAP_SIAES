from uuid import UUID

from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.veiculo_repository import VeiculoRepository


class ExcluirCliente:
    """Exclusão lógica do cliente e dos veículos dele; as OS são preservadas (RF-06, RF-09).

    Os veículos saem na mesma unidade de trabalho, para não restar veículo ativo de cliente
    excluído (RNF-08).
    """

    def __init__(self, clientes: ClienteRepository, veiculos: VeiculoRepository):
        self._clientes = clientes
        self._veiculos = veiculos

    async def executar(self, id: UUID) -> None:
        cliente = await self._clientes.buscar_ativo_por_id(id)
        cliente.excluir()
        await self._clientes.salvar(cliente)
        for veiculo in await self._veiculos.listar(cliente.id):
            veiculo.excluir()
            await self._veiculos.salvar(veiculo)
