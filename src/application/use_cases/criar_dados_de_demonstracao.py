from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from application.use_cases.criar_carga_inicial import (
    ATENDENTE_DE_DEMONSTRACAO,
    MECANICO_DE_DEMONSTRACAO,
)
from domain.entities.cliente import Cliente
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.item_peca import ItemPeca
from domain.entities.item_servico import ItemServico
from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.peca_repository import PecaRepository
from domain.repositories.servico_repository import ServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository
from domain.repositories.veiculo_repository import VeiculoRepository
from domain.value_objects.documento import Documento
from domain.value_objects.filtro_ordens_servico import FiltroOrdensServico
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.orcamento import Orcamento
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor


@dataclass(frozen=True)
class _ServicoDeDemonstracao:
    codigo: str
    nome: str
    descricao: str
    valor_base: str
    tempo_estimado_minutos: int


@dataclass(frozen=True)
class _PecaDeDemonstracao:
    codigo_referencia: str
    nome: str
    preco_unitario: str
    prazo_reposicao_dias: int
    quantidade_fisica: int


@dataclass(frozen=True)
class _ClienteDeDemonstracao:
    nome: str
    documento: str
    email: str
    telefone: str


@dataclass(frozen=True)
class _VeiculoDeDemonstracao:
    cliente: int
    placa: str
    marca: str
    modelo: str
    ano: int


@dataclass(frozen=True)
class _Etapa:
    status: StatusOS
    horas_apos_a_abertura: int
    origem: OrigemTransicao = OrigemTransicao.USUARIO


@dataclass(frozen=True)
class _OSDeDemonstracao:
    veiculo: int
    aberta_ha: timedelta
    etapas: tuple[_Etapa, ...]
    servicos: tuple[str, ...]
    pecas: tuple[tuple[str, int], ...] = ()


_SERVICOS = (
    _ServicoDeDemonstracao(
        "SRV-OLEO", "Troca de óleo e filtro", "Drenagem do óleo e troca do filtro.", "120.00", 40
    ),
    _ServicoDeDemonstracao(
        "SRV-FREIO", "Revisão dos freios", "Inspeção de discos e troca das pastilhas.", "180.00", 90
    ),
    _ServicoDeDemonstracao(
        "SRV-ALINHA", "Alinhamento e balanceamento", "Alinhamento e balanceamento.", "150.00", 60
    ),
    _ServicoDeDemonstracao(
        "SRV-ELETRICA",
        "Diagnóstico elétrico",
        "Leitura da central e teste da bateria.",
        "200.00",
        120,
    ),
    _ServicoDeDemonstracao(
        "SRV-SUSPENSAO", "Troca de amortecedores", "Troca do par dianteiro.", "350.00", 180
    ),
)

# O amortecedor nasce sem saldo para a OS que o pede esperar a reposição (RF-18, RF-19).
_PECAS = (
    _PecaDeDemonstracao("FLT-OLEO-01", "Filtro de óleo", "45.00", 2, 15),
    _PecaDeDemonstracao("PST-FREIO-02", "Pastilha de freio dianteira", "160.00", 3, 6),
    _PecaDeDemonstracao("AMT-DIANT-03", "Amortecedor dianteiro", "420.00", 7, 0),
)

_CLIENTES = (
    _ClienteDeDemonstracao("Ana Souza", "52998224725", "ana.souza@exemplo.com", "11912345678"),
    _ClienteDeDemonstracao("Bruno Lima", "11144477735", "bruno.lima@exemplo.com", "11923456789"),
    _ClienteDeDemonstracao("Carla Mendes", "39053344705", "carla@exemplo.com", "21934567890"),
    _ClienteDeDemonstracao("Daniel Rocha", "98765432100", "daniel@exemplo.com", "31945678901"),
    _ClienteDeDemonstracao(
        "Transportes Rápidos Ltda", "11222333000181", "frota@exemplo.com", "1134567890"
    ),
)

_VEICULOS = (
    _VeiculoDeDemonstracao(0, "ABC1D23", "Volkswagen", "Gol", 2018),
    _VeiculoDeDemonstracao(1, "BRA2E19", "Fiat", "Argo", 2021),
    _VeiculoDeDemonstracao(2, "CDE3F45", "Chevrolet", "Onix", 2020),
    _VeiculoDeDemonstracao(3, "DEF4567", "Toyota", "Corolla", 2016),
    _VeiculoDeDemonstracao(4, "FRT5G67", "Mercedes-Benz", "Sprinter", 2022),
)

_RECEBIDA = (_Etapa(StatusOS.RECEBIDA, 0),)
_EM_DIAGNOSTICO = (*_RECEBIDA, _Etapa(StatusOS.EM_DIAGNOSTICO, 1))
_AGUARDANDO_APROVACAO = (*_EM_DIAGNOSTICO, _Etapa(StatusOS.AGUARDANDO_APROVACAO, 3))
_AGUARDANDO_PECA = (
    *_AGUARDANDO_APROVACAO,
    _Etapa(StatusOS.AGUARDANDO_PECA, 5, OrigemTransicao.CLIENTE),
)
_AGUARDANDO_EXECUCAO = (
    *_AGUARDANDO_APROVACAO,
    _Etapa(StatusOS.AGUARDANDO_EXECUCAO, 6, OrigemTransicao.CLIENTE),
)
_EM_EXECUCAO = (*_AGUARDANDO_EXECUCAO, _Etapa(StatusOS.EM_EXECUCAO, 24))
_FINALIZADA = (*_EM_EXECUCAO, _Etapa(StatusOS.FINALIZADA, 27))
_ENTREGUE = (*_FINALIZADA, _Etapa(StatusOS.ENTREGUE, 30))
_ENTREGUE_APOS_ESPERAR_PECA = (
    *_AGUARDANDO_PECA,
    _Etapa(StatusOS.AGUARDANDO_EXECUCAO, 72, OrigemTransicao.SISTEMA),
    _Etapa(StatusOS.EM_EXECUCAO, 74),
    _Etapa(StatusOS.FINALIZADA, 77),
    _Etapa(StatusOS.ENTREGUE, 96),
)
_CANCELADA = (*_AGUARDANDO_APROVACAO, _Etapa(StatusOS.CANCELADA, 8, OrigemTransicao.CLIENTE))

# Uma OS em cada status (Linguagem Ubíqua §5), da mais antiga para a mais nova, que é a ordem
# em que o saldo é reservado (RF-18). As duas entregues caem em meses diferentes, e uma delas
# esperou peça, para o relatório de tempos médios ter o que agrupar (RF-27).
_ORDENS = (
    _OSDeDemonstracao(3, timedelta(days=40), _ENTREGUE, ("SRV-ALINHA",)),
    _OSDeDemonstracao(
        4,
        timedelta(days=20),
        _ENTREGUE_APOS_ESPERAR_PECA,
        ("SRV-SUSPENSAO", "SRV-ALINHA"),
        (("AMT-DIANT-03", 2),),
    ),
    _OSDeDemonstracao(0, timedelta(days=6), _FINALIZADA, ("SRV-OLEO",), (("FLT-OLEO-01", 1),)),
    _OSDeDemonstracao(2, timedelta(days=4), _CANCELADA, ("SRV-ELETRICA",)),
    _OSDeDemonstracao(1, timedelta(days=3), _EM_EXECUCAO, ("SRV-FREIO",), (("PST-FREIO-02", 1),)),
    _OSDeDemonstracao(
        3, timedelta(days=2), _AGUARDANDO_PECA, ("SRV-SUSPENSAO",), (("AMT-DIANT-03", 2),)
    ),
    _OSDeDemonstracao(
        4,
        timedelta(hours=40),
        _AGUARDANDO_EXECUCAO,
        ("SRV-FREIO", "SRV-OLEO"),
        (("PST-FREIO-02", 1), ("FLT-OLEO-01", 1)),
    ),
    _OSDeDemonstracao(
        0, timedelta(hours=26), _AGUARDANDO_APROVACAO, ("SRV-FREIO",), (("PST-FREIO-02", 1),)
    ),
    _OSDeDemonstracao(2, timedelta(hours=5), _EM_DIAGNOSTICO, ("SRV-OLEO",), (("FLT-OLEO-01", 1),)),
    _OSDeDemonstracao(1, timedelta(hours=1), _RECEBIDA, ()),
)

_COM_ORCAMENTO = frozenset(StatusOS) - {StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO}
_COM_RESERVA_NO_SALDO = {
    StatusOS.AGUARDANDO_APROVACAO,
    StatusOS.AGUARDANDO_PECA,
    StatusOS.AGUARDANDO_EXECUCAO,
}
_COM_BAIXA_REALIZADA = {StatusOS.EM_EXECUCAO, StatusOS.FINALIZADA, StatusOS.ENTREGUE}
_REGISTRADOS_PELO_ATENDENTE = {StatusOS.RECEBIDA, StatusOS.ENTREGUE}


class CriarDadosDeDemonstracao:
    """Cria o catálogo, os clientes e uma OS em cada status, com datas passadas, para a
    demonstração da aplicação (`SEED_DEMO=true`).

    As OS são reconstituídas pelo construtor, com o histórico escrito aqui, porque as transições
    gravam sempre o instante atual e o histórico gravado não pode ser alterado (RF-24). As
    reservas seguem o RF-18: a OS que espera aprovação, peça ou execução reserva o saldo pela
    ordem de abertura, e a OS que já iniciou a execução teve a baixa feita antes, fora do saldo
    atual. Serviço e peça já cadastrados com o mesmo código são reaproveitados, e as OS só são
    criadas se o banco não tiver nenhuma, para a reinicialização não duplicar nem desfazer nada.
    """

    def __init__(
        self,
        usuarios: UsuarioRepository,
        servicos: ServicoRepository,
        pecas: PecaRepository,
        estoques: EstoqueRepository,
        clientes: ClienteRepository,
        veiculos: VeiculoRepository,
        ordens: OrdemServicoRepository,
    ):
        self._usuarios = usuarios
        self._servicos = servicos
        self._pecas = pecas
        self._estoques = estoques
        self._clientes = clientes
        self._veiculos = veiculos
        self._ordens = ordens

    async def executar(self, momento: datetime) -> None:
        """O `momento` é o instante da subida, a partir do qual as datas das OS são recuadas."""
        servicos = {dados.codigo: await self._servico_cadastrado(dados) for dados in _SERVICOS}
        pecas = {dados.codigo_referencia: await self._peca_cadastrada(dados) for dados in _PECAS}
        if await self._ordens.listar(FiltroOrdensServico()):
            return
        atendente = await self._usuarios.buscar_por_email(ATENDENTE_DE_DEMONSTRACAO.email)
        mecanico = await self._usuarios.buscar_por_email(MECANICO_DE_DEMONSTRACAO.email)
        veiculos = await self._veiculos_cadastrados()
        estoques = {
            codigo: await self._estoques.buscar_por_peca(peca.id) for codigo, peca in pecas.items()
        }
        for dados in _ORDENS:
            cliente, veiculo = veiculos[dados.veiculo]
            itens_de_servico = [
                ItemServico.a_partir_de(servicos[codigo]) for codigo in dados.servicos
            ]
            historico = _historico(dados.etapas, momento - dados.aberta_ha, atendente, mecanico)
            status = historico[-1].status_novo
            itens_de_peca = [
                _item_de_peca(pecas[codigo], quantidade, status, estoques[codigo])
                for codigo, quantidade in dados.pecas
            ]
            await self._ordens.salvar(
                _ordem_servico(
                    cliente, veiculo, mecanico, historico, itens_de_servico, itens_de_peca
                )
            )
        for estoque in estoques.values():
            await self._estoques.salvar(estoque)

    async def _servico_cadastrado(self, dados: _ServicoDeDemonstracao) -> Servico:
        if servico := await self._servicos.buscar_por_codigo(dados.codigo):
            return servico
        servico = Servico(
            codigo=dados.codigo,
            nome=dados.nome,
            descricao=dados.descricao,
            valor_base=Valor(dados.valor_base),
            tempo_estimado_minutos=dados.tempo_estimado_minutos,
        )
        await self._servicos.salvar(servico)
        return servico

    async def _peca_cadastrada(self, dados: _PecaDeDemonstracao) -> Peca:
        if peca := await self._pecas.buscar_por_codigo_referencia(dados.codigo_referencia):
            return peca
        peca = Peca(
            codigo_referencia=dados.codigo_referencia,
            nome=dados.nome,
            preco_unitario=Valor(dados.preco_unitario),
            prazo_reposicao_dias=dados.prazo_reposicao_dias,
        )
        await self._pecas.salvar(peca)
        await self._estoques.salvar(
            EstoquePeca(peca_id=peca.id, quantidade_fisica=dados.quantidade_fisica)
        )
        return peca

    async def _veiculos_cadastrados(self) -> list[tuple[Cliente, Veiculo]]:
        clientes = [await self._cliente_cadastrado(dados) for dados in _CLIENTES]
        return [
            (
                clientes[dados.cliente],
                await self._veiculo_cadastrado(clientes[dados.cliente], dados),
            )
            for dados in _VEICULOS
        ]

    async def _cliente_cadastrado(self, dados: _ClienteDeDemonstracao) -> Cliente:
        documento = Documento.de_texto(dados.documento)
        if cliente := await self._clientes.buscar_por_documento(documento):
            return cliente
        cliente = Cliente(
            nome=dados.nome, documento=documento, email=dados.email, telefone=dados.telefone
        )
        await self._clientes.salvar(cliente)
        return cliente

    async def _veiculo_cadastrado(self, cliente: Cliente, dados: _VeiculoDeDemonstracao) -> Veiculo:
        placa = Placa(dados.placa)
        if veiculo := await self._veiculos.buscar_por_placa(placa):
            return veiculo
        veiculo = Veiculo(
            cliente_id=cliente.id,
            placa=placa,
            marca=dados.marca,
            modelo=dados.modelo,
            ano=dados.ano,
        )
        await self._veiculos.salvar(veiculo)
        return veiculo


def _historico(
    etapas: tuple[_Etapa, ...], abertura: datetime, atendente: Usuario, mecanico: Usuario
) -> tuple[HistoricoStatusOS, ...]:
    anteriores = (None, *(etapa.status for etapa in etapas))
    return tuple(
        HistoricoStatusOS(
            status_anterior=anterior,
            status_novo=etapa.status,
            data_hora=abertura + timedelta(hours=etapa.horas_apos_a_abertura),
            origem=etapa.origem,
            usuario_id=_responsavel(etapa, atendente, mecanico),
        )
        for anterior, etapa in zip(anteriores, etapas, strict=False)
    )


def _responsavel(etapa: _Etapa, atendente: Usuario, mecanico: Usuario) -> UUID | None:
    if etapa.origem is not OrigemTransicao.USUARIO:
        return None
    return atendente.id if etapa.status in _REGISTRADOS_PELO_ATENDENTE else mecanico.id


def _item_de_peca(peca: Peca, quantidade: int, status: StatusOS, estoque: EstoquePeca) -> ItemPeca:
    item = ItemPeca.a_partir_de(peca, quantidade)
    if status in _COM_RESERVA_NO_SALDO:
        item.quantidade_reservada, item.quantidade_pendente = estoque.reservar(quantidade)
    elif status in _COM_BAIXA_REALIZADA:
        item.quantidade_reservada = quantidade
    return item


def _ordem_servico(
    cliente: Cliente,
    veiculo: Veiculo,
    mecanico: Usuario,
    historico: tuple[HistoricoStatusOS, ...],
    servicos: list[ItemServico],
    pecas: list[ItemPeca],
) -> OrdemServico:
    abertura, status = historico[0], historico[-1].status_novo
    id = uuid4()
    return OrdemServico(
        numero=NumeroOS.gerar(cliente.documento, id),
        cliente_id=cliente.id,
        veiculo_id=veiculo.id,
        atendente_id=abertura.usuario_id,
        mecanico_id=mecanico.id if status is not StatusOS.RECEBIDA else None,
        id=id,
        status=status,
        data_abertura=abertura.data_hora,
        data_inicio_execucao=_entrada_em(historico, StatusOS.EM_EXECUCAO),
        data_finalizacao=_entrada_em(historico, StatusOS.FINALIZADA),
        servicos=servicos,
        pecas=pecas,
        orcamento=_orcamento(servicos, pecas) if status in _COM_ORCAMENTO else None,
        historico=historico,
    )


def _entrada_em(historico: tuple[HistoricoStatusOS, ...], status: StatusOS) -> datetime | None:
    return next(
        (registro.data_hora for registro in historico if registro.status_novo is status), None
    )


def _orcamento(servicos: list[ItemServico], pecas: list[ItemPeca]) -> Orcamento:
    return Orcamento(
        subtotal_servicos=_somar(item.preco_congelado for item in servicos),
        subtotal_pecas=_somar(item.valor_total() for item in pecas),
    )


def _somar(valores: Iterable[Valor]) -> Valor:
    total = Valor(0)
    for valor in valores:
        total = total.somar(valor)
    return total
