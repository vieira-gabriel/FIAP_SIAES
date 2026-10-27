from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.veiculo import Veiculo
from domain.value_objects.placa import Placa


class VeiculoRepository(ABC):
    @abstractmethod
    async def salvar(self, veiculo: Veiculo) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Veiculo | None: ...

    @abstractmethod
    async def buscar_por_placa(self, placa: Placa) -> Veiculo | None: ...
