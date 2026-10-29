"""Adaptador da OS com PostgreSQL real (RF-13, RF-19, RF-24, RNF-08, RNF-09, RNF-11)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from application.use_cases.finalizar_orcamento import FinalizarOrcamento
from domain.entities.cliente import Cliente
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.exceptions import ItemIndisponivel, NumeroOSJaCadastrado
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
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


@pytest.fixture
def fabrica_de_sessoes(banco_migrado):
    return criar_fabrica_de_sessoes(banco_migrado)


class Cadastros:
    """Linhas de que a OS depende pelas chaves estrangeiras."""

    def __init__(self):
        self.atendente = Usuario(
            nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=PerfilUsuario.ATENDENTE
        )
        self.mecanico = Usuario(
            nome="Bruno", email="bruno@oficina.com", senha_hash="h", perfil=PerfilUsuario.MECANICO
        )
        self.cliente = Cliente(
            nome="Carla",
            documento=CPF("529.982.247-25"),
            email="carla@email.com",
            telefone="11999990000",
        )
        self.veiculo = Veiculo(
            cliente_id=self.cliente.id,
            placa=Placa("ABC1D23"),
            marca="Fiat",
            modelo="Uno",
            ano=2020,
        )
        self.servico = Servico(
            codigo="SRV-001",
            nome="Troca de óleo",
            descricao="Troca do óleo do motor",
            valor_base=Valor("120.00"),
            tempo_estimado_minutos=45,
        )
        self.filtro = _peca("FLT-001", "Filtro de óleo", "35.90")
        self.vela = _peca("VEL-001", "Vela de ignição", "20.00")


def _peca(codigo: str, nome: str, preco: str) -> Peca:
    return Peca(
        codigo_referencia=codigo, nome=nome, preco_unitario=Valor(preco), prazo_reposicao_dias=3
    )


@pytest.fixture
async def cadastros(fabrica_de_sessoes) -> Cadastros:
    dados = Cadastros()
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        sessao = unidade.sessao
        usuarios = PostgresUsuarioRepository(sessao)
        await usuarios.salvar(dados.atendente)
        await usuarios.salvar(dados.mecanico)
        await PostgresClienteRepository(sessao).salvar(dados.cliente)
        await sessao.flush()
        await PostgresVeiculoRepository(sessao).salvar(dados.veiculo)
        await PostgresServicoRepository(sessao).salvar(dados.servico)
        for peca in (dados.filtro, dados.vela):
            await PostgresPecaRepository(sessao).salvar(peca)
            await PostgresEstoqueRepository(sessao).salvar(EstoquePeca(peca_id=peca.id))
    return dados


def _abrir(cadastros: Cadastros, numero: str = "529-7F3A9C2B") -> OrdemServico:
    return OrdemServico.abrir(
        numero=NumeroOS(numero),
        cliente_id=cadastros.cliente.id,
        veiculo_id=cadastros.veiculo.id,
        atendente_id=cadastros.atendente.id,
    )


def _orcada(cadastros: Cadastros, numero: str = "529-7F3A9C2B") -> OrdemServico:
    """Em `AGUARDANDO_APROVACAO`, com o filtro e a vela pendentes."""
    os = _abrir(cadastros, numero)
    os.atribuir_mecanico(cadastros.mecanico.id)
    os.incluir_servico(cadastros.servico)
    os.incluir_peca(cadastros.filtro, quantidade=2)
    os.incluir_peca(cadastros.vela, quantidade=4)
    os.finalizar_orcamento(
        cadastros.mecanico.id, [cadastros.servico], [cadastros.filtro, cadastros.vela]
    )
    return os


async def _salvar(fabrica_de_sessoes, os: OrdemServico) -> None:
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        await PostgresOrdemServicoRepository(unidade.sessao).salvar(os)


async def _buscar(fabrica_de_sessoes, os_id) -> OrdemServico:
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        return await PostgresOrdemServicoRepository(unidade.sessao).buscar_por_id(os_id)


async def test_salva_e_recarrega_a_os_com_itens_historico_e_valores_congelados(
    fabrica_de_sessoes, cadastros
):
    os = _orcada(cadastros)
    os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente = 1, 1
    await _salvar(fabrica_de_sessoes, os)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)
        por_id = await ordens.buscar_por_id(os.id)
        por_numero = await ordens.buscar_por_numero(NumeroOS("529-7F3A9C2B"))

    assert por_id == por_numero == os
    assert (por_id.numero, por_id.status, por_id.mecanico_id) == (
        os.numero,
        StatusOS.AGUARDANDO_APROVACAO,
        cadastros.mecanico.id,
    )
    assert (por_id.cliente_id, por_id.veiculo_id, por_id.atendente_id) == (
        os.cliente_id,
        os.veiculo_id,
        os.atendente_id,
    )
    assert (por_id.data_abertura, por_id.data_inicio_execucao) == (os.data_abertura, None)
    assert vars(por_id.servicos[0]) == vars(os.servicos[0])
    assert [vars(item) for item in por_id.pecas] == [vars(item) for item in os.pecas]
    assert por_id.orcamento == os.orcamento
    assert por_id.orcamento.total == Valor("271.80")
    assert por_id.historico == os.historico


async def test_os_sem_orcamento_e_sem_itens_volta_sem_orcamento(fabrica_de_sessoes, cadastros):
    os = _abrir(cadastros)
    await _salvar(fabrica_de_sessoes, os)

    salva = await _buscar(fabrica_de_sessoes, os.id)

    assert (salva.orcamento, salva.servicos, salva.pecas) == (None, [], [])
    assert salva.historico == os.historico


async def test_busca_inexistente_devolve_nada(fabrica_de_sessoes, cadastros):
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)

        assert await ordens.buscar_por_id(uuid4()) is None
        assert await ordens.buscar_por_numero(NumeroOS("111-00000000")) is None


async def test_salvar_de_novo_insere_so_o_registro_novo_e_remove_o_item_retirado(
    fabrica_de_sessoes, cadastros
):
    os = _abrir(cadastros)
    os.atribuir_mecanico(cadastros.mecanico.id)
    os.incluir_peca(cadastros.filtro, quantidade=1)
    os.incluir_peca(cadastros.vela, quantidade=1)
    await _salvar(fabrica_de_sessoes, os)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)
        carregada = await ordens.buscar_por_id(os.id)
        carregada.remover_peca(cadastros.vela.id)
        carregada.cancelar(cadastros.mecanico.id, "Cliente desistiu")
        await ordens.salvar(carregada)

    salva = await _buscar(fabrica_de_sessoes, os.id)
    assert [item.peca_id for item in salva.pecas] == [cadastros.filtro.id]
    assert [r.status_novo for r in salva.historico] == [
        StatusOS.RECEBIDA,
        StatusOS.EM_DIAGNOSTICO,
        StatusOS.CANCELADA,
    ]
    assert salva.historico[-1].motivo == "Cliente desistiu"


async def test_itens_voltam_em_ordem_de_nome(fabrica_de_sessoes, cadastros):
    os = _abrir(cadastros)
    os.atribuir_mecanico(cadastros.mecanico.id)
    os.incluir_peca(cadastros.vela, quantidade=1)
    os.incluir_peca(cadastros.filtro, quantidade=1)
    await _salvar(fabrica_de_sessoes, os)

    salva = await _buscar(fabrica_de_sessoes, os.id)

    assert [item.nome for item in salva.pecas] == ["Filtro de óleo", "Vela de ignição"]


async def test_registros_do_mesmo_instante_voltam_na_ordem_do_encadeamento(
    fabrica_de_sessoes, cadastros
):
    """Duas transições na mesma transação podem receber o mesmo horário do relógio."""
    instante = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
    historico = (
        HistoricoStatusOS(None, StatusOS.RECEBIDA, instante, OrigemTransicao.SISTEMA),
        HistoricoStatusOS(
            StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO, instante, OrigemTransicao.SISTEMA
        ),
        HistoricoStatusOS(
            StatusOS.EM_DIAGNOSTICO, StatusOS.CANCELADA, instante, OrigemTransicao.SISTEMA
        ),
    )
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=cadastros.cliente.id,
        veiculo_id=cadastros.veiculo.id,
        atendente_id=cadastros.atendente.id,
        status=StatusOS.CANCELADA,
        data_abertura=instante,
        historico=historico,
    )
    await _salvar(fabrica_de_sessoes, os)

    for _ in range(5):
        assert (await _buscar(fabrica_de_sessoes, os.id)).historico == historico


async def test_pendencias_da_peca_da_abertura_mais_antiga_a_mais_nova(
    fabrica_de_sessoes, cadastros
):
    mais_nova = _orcada(cadastros, "529-00000002")
    mais_antiga = _orcada(cadastros, "529-00000001")
    mais_antiga.data_abertura = mais_nova.data_abertura - timedelta(days=1)
    sem_pendencia = _orcada(cadastros, "529-00000003")
    sem_pendencia.rejeitar_orcamento()
    for os in (mais_nova, mais_antiga, sem_pendencia):
        await _salvar(fabrica_de_sessoes, os)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        pendentes = await PostgresOrdemServicoRepository(unidade.sessao).listar_pendentes_da_peca(
            cadastros.filtro.id
        )

    assert [os.numero.valor for os in pendentes] == ["529-00000001", "529-00000002"]


async def test_numero_repetido_vira_excecao_do_dominio(fabrica_de_sessoes, cadastros):
    await _salvar(fabrica_de_sessoes, _abrir(cadastros))

    with pytest.raises(NumeroOSJaCadastrado):
        await _salvar(fabrica_de_sessoes, _abrir(cadastros))


@pytest.mark.parametrize(
    "comando",
    [
        "UPDATE historico_status_os SET motivo = 'alterado' WHERE os_id = :id",
        "DELETE FROM historico_status_os WHERE os_id = :id",
        "TRUNCATE historico_status_os",
    ],
    ids=["update", "delete", "truncate"],
)
async def test_banco_recusa_alterar_ou_remover_o_historico(fabrica_de_sessoes, cadastros, comando):
    os = _abrir(cadastros)
    await _salvar(fabrica_de_sessoes, os)

    with pytest.raises(DBAPIError, match="só aceita inserção"):
        async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
            await unidade.sessao.execute(text(comando), {"id": os.id})


async def test_os_lida_fica_bloqueada_ate_o_fim_da_transacao(fabrica_de_sessoes, cadastros):
    """Duas operações na mesma OS esperam uma pela outra (RNF-09)."""
    os = _abrir(cadastros)
    await _salvar(fabrica_de_sessoes, os)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as primeira:
        await PostgresOrdemServicoRepository(primeira.sessao).buscar_por_id(os.id)

        with pytest.raises(DBAPIError, match="lock timeout"):
            async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as segunda:
                await segunda.sessao.execute(text("SET LOCAL lock_timeout = '200ms'"))
                await PostgresOrdemServicoRepository(segunda.sessao).buscar_por_numero(os.numero)


async def test_lista_de_pendencias_nao_bloqueia_as_os(fabrica_de_sessoes, cadastros):
    """Quem lista já bloqueou o estoque; bloquear as OS depois dele causaria impasse com o
    cancelamento, que bloqueia a OS e depois o estoque."""
    os = _orcada(cadastros)
    await _salvar(fabrica_de_sessoes, os)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as primeira:
        await PostgresOrdemServicoRepository(primeira.sessao).listar_pendentes_da_peca(
            cadastros.filtro.id
        )

        async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as segunda:
            await segunda.sessao.execute(text("SET LOCAL lock_timeout = '200ms'"))
            lida = await PostgresOrdemServicoRepository(segunda.sessao).buscar_por_id(os.id)

    assert lida == os


async def test_finalizar_orcamento_recusa_peca_excluida_depois_de_incluida(
    fabrica_de_sessoes, cadastros
):
    os = _abrir(cadastros)
    os.atribuir_mecanico(cadastros.mecanico.id)
    os.incluir_peca(cadastros.filtro, quantidade=1)
    await _salvar(fabrica_de_sessoes, os)
    cadastros.filtro.excluir([])
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        await PostgresPecaRepository(unidade.sessao).salvar(cadastros.filtro)

    with pytest.raises(ItemIndisponivel):
        async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
            sessao = unidade.sessao
            await FinalizarOrcamento(
                PostgresOrdemServicoRepository(sessao),
                PostgresEstoqueRepository(sessao),
                PostgresServicoRepository(sessao),
                PostgresPecaRepository(sessao),
            ).executar(os.id, cadastros.mecanico.id)

    assert (await _buscar(fabrica_de_sessoes, os.id)).status is StatusOS.EM_DIAGNOSTICO


async def test_finalizar_orcamento_espera_a_exclusao_da_peca_em_andamento(
    fabrica_de_sessoes, cadastros
):
    """A exclusão bloqueia o estoque; a conclusão espera e então vê a peça excluída (RF-12)."""
    os = _abrir(cadastros)
    os.atribuir_mecanico(cadastros.mecanico.id)
    os.incluir_peca(cadastros.filtro, quantidade=1)
    await _salvar(fabrica_de_sessoes, os)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as exclusao:
        await PostgresEstoqueRepository(exclusao.sessao).buscar_por_peca(cadastros.filtro.id)

        with pytest.raises(DBAPIError, match="lock timeout"):
            async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
                sessao = unidade.sessao
                await sessao.execute(text("SET LOCAL lock_timeout = '200ms'"))
                await FinalizarOrcamento(
                    PostgresOrdemServicoRepository(sessao),
                    PostgresEstoqueRepository(sessao),
                    PostgresServicoRepository(sessao),
                    PostgresPecaRepository(sessao),
                ).executar(os.id, cadastros.mecanico.id)
