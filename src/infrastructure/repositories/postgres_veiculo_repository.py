from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.veiculo import Veiculo
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.placa import Placa
from infrastructure.database.veiculo_model import VeiculoModel


class PostgresVeiculoRepository(VeiculoRepository):
    """Usa a sessão da unidade de trabalho; quem confirma a transação é ela (RNF-08)."""

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, veiculo: Veiculo) -> None:
        await self._sessao.merge(_para_modelo(veiculo))

    async def buscar_por_id(self, id: UUID) -> Veiculo | None:
        modelo = await self._sessao.get(VeiculoModel, id)
        return _para_entidade(modelo) if modelo else None

    async def buscar_por_placa(self, placa: Placa) -> Veiculo | None:
        consulta = select(VeiculoModel).where(
            VeiculoModel.placa == placa.valor, VeiculoModel.ativo.is_(True)
        )
        modelo = await self._sessao.scalar(consulta)
        return _para_entidade(modelo) if modelo else None

    async def listar_por_placa(self, placa: Placa) -> list[Veiculo]:
        modelos = await self._sessao.scalars(
            select(VeiculoModel).where(VeiculoModel.placa == placa.valor)
        )
        return [_para_entidade(modelo) for modelo in modelos]

    async def listar(self, cliente_id: UUID | None = None) -> list[Veiculo]:
        consulta = select(VeiculoModel).where(VeiculoModel.ativo.is_(True))
        if cliente_id is not None:
            consulta = consulta.where(VeiculoModel.cliente_id == cliente_id)
        modelos = await self._sessao.scalars(consulta.order_by(VeiculoModel.placa))
        return [_para_entidade(modelo) for modelo in modelos]


def _para_modelo(veiculo: Veiculo) -> VeiculoModel:
    return VeiculoModel(
        id=veiculo.id,
        cliente_id=veiculo.cliente_id,
        placa=veiculo.placa.valor,
        marca=veiculo.marca,
        modelo=veiculo.modelo,
        ano=veiculo.ano,
        ativo=veiculo.ativo,
    )


def _para_entidade(modelo: VeiculoModel) -> Veiculo:
    return Veiculo(
        id=modelo.id,
        cliente_id=modelo.cliente_id,
        placa=Placa(modelo.placa),
        marca=modelo.marca,
        modelo=modelo.modelo,
        ano=modelo.ano,
        ativo=modelo.ativo,
    )
