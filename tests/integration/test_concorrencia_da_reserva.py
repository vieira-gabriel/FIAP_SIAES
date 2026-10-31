"""Duas conclusões de orçamento disputando a mesma peça, em transações reais (RNF-09, RF-12,
RF-18).

Usa um banco só deste teste (`banco_migrado`): as fixtures comuns prendem todas as sessões numa
transação só, e aqui cada conclusão precisa da própria conexão e do próprio commit.
"""

import asyncio
from dataclasses import dataclass

import pytest

from application.events.event_dispatcher import EventDispatcher
from application.handlers.reserva_pecas_handler import ReservaPecasHandler
from application.use_cases.finalizar_orcamento import FinalizarOrcamento
from domain.entities.cliente import Cliente
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor
from infrastructure.database.engine import criar_fabrica_de_sessoes
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_cliente_repository import PostgresClienteRepository
from infrastructure.repositories.postgres_estoque_repository import PostgresEstoqueRepository
from infrastructure.repositories.postgres_ordem_servico_repository import (
    PostgresOrdemServicoRepository,
)
from infrastructure.repositories.postgres_peca_repository import PostgresPecaRepository
from infrastructure.repositories.postgres_servico_repository import PostgresServicoRepository
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.repositories.postgres_veiculo_repository import PostgresVeiculoRepository

# Tempo para a segunda conclusão chegar ao bloqueio do estoque; folgado para o CI.
ESPERA_PELO_BLOQUEIO = 1.0


@dataclass
class Disputa:
    """Uma peça com uma unidade só e duas OS em diagnóstico, cada uma pedindo uma."""

    mecanico: Usuario
    peca: Peca
    primeira: OrdemServico
    segunda: OrdemServico


@pytest.fixture
def fabrica_de_sessoes(banco_migrado):
    return criar_fabrica_de_sessoes(banco_migrado)


@pytest.fixture
async def disputa(fabrica_de_sessoes) -> Disputa:
    atendente = Usuario(
        nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=PerfilUsuario.ATENDENTE
    )
    mecanico = Usuario(
        nome="Bruno", email="bruno@oficina.com", senha_hash="h", perfil=PerfilUsuario.MECANICO
    )
    cliente = Cliente(
        nome="Carla", documento=CPF("529.982.247-25"), email="c@email.com", telefone="11999990000"
    )
    veiculo = Veiculo(
        cliente_id=cliente.id, placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2020
    )
    peca = Peca(
        codigo_referencia="FLT-001",
        nome="Filtro de óleo",
        preco_unitario=Valor("35.90"),
        prazo_reposicao_dias=3,
    )
    primeira, segunda = (
        _em_diagnostico(numero, cliente, veiculo, atendente, mecanico, peca)
        for numero in ("529-00000001", "529-00000002")
    )
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        sessao = unidade.sessao
        await PostgresUsuarioRepository(sessao).salvar(atendente)
        await PostgresUsuarioRepository(sessao).salvar(mecanico)
        await PostgresClienteRepository(sessao).salvar(cliente)
        await sessao.flush()
        await PostgresVeiculoRepository(sessao).salvar(veiculo)
        await PostgresPecaRepository(sessao).salvar(peca)
        await PostgresEstoqueRepository(sessao).salvar(
            EstoquePeca(peca_id=peca.id, quantidade_fisica=1)
        )
        for os in (primeira, segunda):
            await PostgresOrdemServicoRepository(sessao).salvar(os)
    return Disputa(mecanico, peca, primeira, segunda)


def _em_diagnostico(numero, cliente, veiculo, atendente, mecanico, peca) -> OrdemServico:
    os = OrdemServico.abrir(
        numero=NumeroOS(numero),
        cliente_id=cliente.id,
        veiculo_id=veiculo.id,
        atendente_id=atendente.id,
    )
    os.atribuir_mecanico(mecanico, mecanico)
    os.incluir_peca(peca, quantidade=1)
    return os


def _conclusao(sessao) -> FinalizarOrcamento:
    """Montada como no container: a reserva reage ao evento na mesma transação (RNF-08)."""
    ordens = PostgresOrdemServicoRepository(sessao)
    estoques = PostgresEstoqueRepository(sessao)
    eventos = EventDispatcher()
    eventos.registrar(OrcamentoFinalizadoEvent, ReservaPecasHandler(ordens, estoques))
    return FinalizarOrcamento(
        ordens, estoques, PostgresServicoRepository(sessao), PostgresPecaRepository(sessao), eventos
    )


async def _concluir_orcamento(fabrica_de_sessoes, os: OrdemServico, disputa: Disputa) -> None:
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        await _conclusao(unidade.sessao).executar(os.id, disputa.mecanico.id)


async def _item_gravado(fabrica_de_sessoes, os: OrdemServico):
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        gravada = await PostgresOrdemServicoRepository(unidade.sessao).buscar_por_id(os.id)
    assert gravada.status is StatusOS.AGUARDANDO_APROVACAO
    (item,) = gravada.pecas
    return item


async def _estoque_gravado(fabrica_de_sessoes, disputa: Disputa) -> EstoquePeca:
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        return await PostgresEstoqueRepository(unidade.sessao).buscar_por_peca(disputa.peca.id)


async def _assert_uma_reservada_e_outra_pendente(fabrica_de_sessoes, disputa, reservada, pendente):
    item_reservado = await _item_gravado(fabrica_de_sessoes, reservada)
    item_pendente = await _item_gravado(fabrica_de_sessoes, pendente)
    estoque = await _estoque_gravado(fabrica_de_sessoes, disputa)

    assert (item_reservado.quantidade_reservada, item_reservado.quantidade_pendente) == (1, 0)
    assert (item_pendente.quantidade_reservada, item_pendente.quantidade_pendente) == (0, 1)
    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (1, 1)
    assert estoque.saldo_disponivel() == 0


async def test_segunda_conclusao_espera_a_primeira_e_fica_com_a_pendencia(
    fabrica_de_sessoes, disputa
):
    """A primeira conclusão reserva a unidade e segura o bloqueio do estoque até o commit. A
    segunda espera esse bloqueio e lê o saldo já zerado, em vez do saldo de antes (RNF-09)."""
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as primeira:
        await _conclusao(primeira.sessao).executar(disputa.primeira.id, disputa.mecanico.id)
        segunda = asyncio.create_task(
            _concluir_orcamento(fabrica_de_sessoes, disputa.segunda, disputa)
        )
        concluidas, _ = await asyncio.wait({segunda}, timeout=ESPERA_PELO_BLOQUEIO)

        assert not concluidas
    await segunda

    await _assert_uma_reservada_e_outra_pendente(
        fabrica_de_sessoes, disputa, reservada=disputa.primeira, pendente=disputa.segunda
    )


async def test_duas_conclusoes_ao_mesmo_tempo_nao_deixam_o_saldo_negativo(
    fabrica_de_sessoes, disputa
):
    """Sem ordem imposta: qualquer uma pode ganhar, mas só uma fica com a unidade (RF-12)."""
    await asyncio.gather(
        _concluir_orcamento(fabrica_de_sessoes, disputa.primeira, disputa),
        _concluir_orcamento(fabrica_de_sessoes, disputa.segunda, disputa),
    )

    primeira_venceu = (
        await _item_gravado(fabrica_de_sessoes, disputa.primeira)
    ).quantidade_reservada
    vencedora, perdedora = (
        (disputa.primeira, disputa.segunda)
        if primeira_venceu
        else (disputa.segunda, disputa.primeira)
    )
    await _assert_uma_reservada_e_outra_pendente(
        fabrica_de_sessoes, disputa, reservada=vencedora, pendente=perdedora
    )
