from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada, PlacaJaCadastrada
from domain.value_objects.placa import Placa


class VeiculoRepository(ABC):
    @abstractmethod
    async def salvar(self, veiculo: Veiculo) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Veiculo | None: ...

    @abstractmethod
    async def buscar_por_placa(self, placa: Placa) -> Veiculo | None:
        """Só o veículo ativo: a placa de um excluído pode pertencer a um novo cadastro (RF-07)."""

    @abstractmethod
    async def listar(self, cliente_id: UUID | None = None) -> list[Veiculo]:
        """Só os veículos ativos, em ordem de placa; com `cliente_id`, só os desse cliente."""

    async def buscar_ativo_por_id(self, id: UUID) -> Veiculo:
        """Para o cadastro, o veículo excluído deixa de existir; as OS dele continuam (RF-09)."""
        veiculo = await self.buscar_por_id(id)
        if veiculo is None or not veiculo.ativo:
            raise EntidadeNaoEncontrada("Veículo", id)
        return veiculo

    async def garantir_placa_livre(self, veiculo: Veiculo) -> None:
        dono_da_placa = await self.buscar_por_placa(veiculo.placa)
        if dono_da_placa is not None and dono_da_placa != veiculo:
            raise PlacaJaCadastrada()
