from uuid import UUID

from domain.entities.veiculo import Veiculo
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.placa import Placa


class CadastrarVeiculo:
    """Cadastro de veículo vinculado a um cliente ativo (RF-07, RF-08)."""

    def __init__(self, veiculos: VeiculoRepository, clientes: ClienteRepository):
        self._veiculos = veiculos
        self._clientes = clientes

    async def executar(
        self, cliente_id: UUID, placa: Placa, marca: str, modelo: str, ano: int
    ) -> Veiculo:
        cliente = await self._clientes.buscar_ativo_por_id(cliente_id)
        veiculo = Veiculo(cliente_id=cliente.id, placa=placa, marca=marca, modelo=modelo, ano=ano)
        await self._veiculos.garantir_placa_livre(veiculo)
        await self._veiculos.salvar(veiculo)
        return veiculo
