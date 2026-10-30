from dataclasses import dataclass
from uuid import UUID, uuid4

from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.veiculo import Veiculo
from domain.exceptions import (
    EntidadeNaoEncontrada,
    NumeroOSIndisponivel,
    OSDeOutroCliente,
)
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.documento import Documento
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.placa import Placa

MAXIMO_DE_TENTATIVAS_DE_NUMERO = 5


@dataclass(frozen=True)
class DadosDoNovoCliente:
    nome: str
    email: str
    telefone: str


@dataclass(frozen=True)
class DadosDoNovoVeiculo:
    marca: str
    modelo: str
    ano: int


class CriarOS:
    """Abertura de OS em `RECEBIDA` (RF-13).

    Busca o cliente pelo documento e o veículo pela placa. Quando um deles não existe, cria no
    mesmo fluxo, com os dados informados; sem os dados, responde 404. A placa de um veículo de
    outro cliente é recusada (RF-07), e o número é refeito com um novo UUID quando já existe.
    """

    def __init__(
        self,
        clientes: ClienteRepository,
        veiculos: VeiculoRepository,
        ordens: OrdemServicoRepository,
    ):
        self._clientes = clientes
        self._veiculos = veiculos
        self._ordens = ordens

    async def executar(
        self,
        documento: Documento,
        placa: Placa,
        atendente_id: UUID,
        cliente_novo: DadosDoNovoCliente | None = None,
        veiculo_novo: DadosDoNovoVeiculo | None = None,
    ) -> OrdemServico:
        cliente = await self._cliente_ou_novo(documento, cliente_novo)
        veiculo = await self._veiculo_ou_novo(cliente, placa, veiculo_novo)
        os_id, numero = await self._numero_livre(documento)
        os = OrdemServico.abrir(
            numero=numero,
            cliente_id=cliente.id,
            veiculo_id=veiculo.id,
            atendente_id=atendente_id,
            id=os_id,
        )
        await self._ordens.salvar(os)
        return os

    async def _cliente_ou_novo(
        self, documento: Documento, dados: DadosDoNovoCliente | None
    ) -> Cliente:
        cliente = await self._clientes.buscar_por_documento(documento)
        if cliente is not None and cliente.ativo:
            return cliente
        if dados is None:
            raise EntidadeNaoEncontrada("Cliente", documento.valor)
        novo = Cliente(
            nome=dados.nome, documento=documento, email=dados.email, telefone=dados.telefone
        )
        await self._clientes.garantir_documento_livre(novo)
        await self._clientes.salvar(novo)
        return novo

    async def _veiculo_ou_novo(
        self, cliente: Cliente, placa: Placa, dados: DadosDoNovoVeiculo | None
    ) -> Veiculo:
        veiculo = await self._veiculos.buscar_por_placa(placa)
        if veiculo is not None:
            if veiculo.cliente_id != cliente.id:
                raise OSDeOutroCliente()
            return veiculo
        if dados is None:
            raise EntidadeNaoEncontrada("Veículo", placa.valor)
        novo = Veiculo(
            cliente_id=cliente.id,
            placa=placa,
            marca=dados.marca,
            modelo=dados.modelo,
            ano=dados.ano,
        )
        await self._veiculos.garantir_placa_livre(novo)
        await self._veiculos.salvar(novo)
        return novo

    async def _numero_livre(self, documento: Documento) -> tuple[UUID, NumeroOS]:
        for _ in range(MAXIMO_DE_TENTATIVAS_DE_NUMERO):
            os_id = uuid4()
            numero = NumeroOS.gerar(documento, os_id)
            if await self._ordens.buscar_por_numero(numero) is None:
                return os_id, numero
        raise NumeroOSIndisponivel()
