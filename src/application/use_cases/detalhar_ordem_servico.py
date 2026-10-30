from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.veiculo_repository import VeiculoRepository


@dataclass(frozen=True)
class DetalheDaOrdemServico:
    os: OrdemServico
    cliente: Cliente
    veiculo: Veiculo
    estimativa_entrega: datetime | None


class DetalharOrdemServico:
    """Todos os dados de uma OS, com cliente, veículo e a estimativa de entrega (RF-15, RF-25).

    Cliente e veículo são lidos mesmo quando excluídos logicamente: a OS guarda o histórico deles
    (RF-06, RF-09).
    """

    def __init__(
        self,
        ordens: OrdemServicoRepository,
        clientes: ClienteRepository,
        veiculos: VeiculoRepository,
    ):
        self._ordens = ordens
        self._clientes = clientes
        self._veiculos = veiculos

    async def executar(self, id: UUID, momento_consulta: datetime) -> DetalheDaOrdemServico:
        os = await self._ordens.buscar_por_id(id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", id)
        cliente = await self._clientes.buscar_por_id(os.cliente_id)
        veiculo = await self._veiculos.buscar_por_id(os.veiculo_id)
        return DetalheDaOrdemServico(
            os=os,
            cliente=cliente,
            veiculo=veiculo,
            estimativa_entrega=os.estimar_entrega(momento_consulta),
        )
