from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.documento import Documento
from domain.value_objects.filtro_ordens_servico import FiltroOrdensServico
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS


@dataclass(frozen=True)
class CriteriosDaListagem:
    """Critérios como chegam da requisição, antes de documento e placa virarem identificadores."""

    documento: Documento | None = None
    placa: Placa | None = None
    status: StatusOS | None = None
    mecanico_id: UUID | None = None
    abertura_de: datetime | None = None
    abertura_ate: datetime | None = None


@dataclass(frozen=True)
class ResumoDaOrdemServico:
    os: OrdemServico
    cliente: Cliente
    veiculo: Veiculo
    mecanico: Usuario | None


class ListarOrdensServico:
    """OS filtradas por status, mecânico, cliente, veículo e período de abertura (RF-14).

    Documento ou placa sem cadastro não têm OS, então a listagem volta vazia, e não com 404.
    """

    def __init__(
        self,
        ordens: OrdemServicoRepository,
        clientes: ClienteRepository,
        veiculos: VeiculoRepository,
        usuarios: UsuarioRepository,
    ):
        self._ordens = ordens
        self._clientes = clientes
        self._veiculos = veiculos
        self._usuarios = usuarios

    async def executar(self, criterios: CriteriosDaListagem) -> list[ResumoDaOrdemServico]:
        filtro = FiltroOrdensServico(
            status=criterios.status,
            mecanico_id=criterios.mecanico_id,
            abertura_de=criterios.abertura_de,
            abertura_ate=criterios.abertura_ate,
        )
        if criterios.documento is not None:
            cliente = await self._clientes.buscar_por_documento(criterios.documento)
            if cliente is None:
                return []
            filtro = replace(filtro, cliente_id=cliente.id)
        if criterios.placa is not None:
            veiculo = await self._veiculos.buscar_por_placa(criterios.placa)
            if veiculo is None:
                return []
            filtro = replace(filtro, veiculo_id=veiculo.id)

        ordens = await self._ordens.listar(filtro)
        clientes = await _buscar_todos(
            {os.cliente_id for os in ordens}, self._clientes.buscar_por_id
        )
        veiculos = await _buscar_todos(
            {os.veiculo_id for os in ordens}, self._veiculos.buscar_por_id
        )
        mecanicos = await _buscar_todos(
            {os.mecanico_id for os in ordens if os.mecanico_id is not None},
            self._usuarios.buscar_por_id,
        )
        return [
            ResumoDaOrdemServico(
                os=os,
                cliente=clientes[os.cliente_id],
                veiculo=veiculos[os.veiculo_id],
                mecanico=mecanicos.get(os.mecanico_id),
            )
            for os in ordens
        ]


async def _buscar_todos[T](
    ids: Iterable[UUID], buscar: Callable[[UUID], Awaitable[T | None]]
) -> dict[UUID, T | None]:
    """Cada identificador é lido uma vez, mesmo que vários registros o citem."""
    return {id: await buscar(id) for id in ids}
