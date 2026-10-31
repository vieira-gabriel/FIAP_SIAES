from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.events.event_dispatcher import EventDispatcher, EventHandler
from application.handlers.baixa_estoque_handler import BaixaEstoqueHandler
from application.use_cases.iniciar_execucao import IniciarExecucao
from domain.entities.estoque_peca import EstoquePeca
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.exceptions import AcessoNegado, EntidadeNaoEncontrada, TransicaoDeStatusInvalida
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

ANTES = datetime.now(UTC)


@pytest.fixture
def iniciar(ordens, usuarios, estoques) -> IniciarExecucao:
    despachador = EventDispatcher()
    despachador.registrar(ExecucaoIniciadaEvent, BaixaEstoqueHandler(estoques))
    return IniciarExecucao(ordens, usuarios, despachador)


async def _usuario(usuarios, perfil: PerfilUsuario, ativo: bool = True) -> Usuario:
    usuario = Usuario(
        nome=perfil.value.title(),
        email=f"{uuid4().hex[:8]}@oficina.com",
        senha_hash="hash",
        perfil=perfil,
        ativo=ativo,
    )
    await usuarios.salvar(usuario)
    return usuario


async def _os(ordens, estoques, mecanico: Usuario, status=StatusOS.AGUARDANDO_EXECUCAO):
    peca_id = uuid4()
    estoque = EstoquePeca(peca_id=peca_id, quantidade_fisica=5, quantidade_reservada=2)
    await estoques.salvar(estoque)
    item = ItemPeca(
        peca_id=peca_id,
        nome="Filtro de óleo",
        quantidade=2,
        preco_unitario_congelado=Valor("35.90"),
        prazo_reposicao_dias=3,
        quantidade_reservada=2,
        quantidade_pendente=0,
    )
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        mecanico_id=mecanico.id,
        status=status,
        pecas=[item],
    )
    await ordens.salvar(os)
    return os, estoque


async def test_mecanico_atribuido_inicia_a_execucao_e_as_pecas_recebem_baixa(
    iniciar, ordens, usuarios, estoques
):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os, estoque = await _os(ordens, estoques, mecanico)

    iniciada = await iniciar.executar(os.id, mecanico.id)

    assert iniciada.status is StatusOS.EM_EXECUCAO
    assert iniciada.data_inicio_execucao >= ANTES
    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (3, 0)
    registro = iniciada.historico[-1]
    assert (registro.status_novo, registro.usuario_id) == (StatusOS.EM_EXECUCAO, mecanico.id)


async def test_gerente_inicia_a_execucao_de_qualquer_os(iniciar, ordens, usuarios, estoques):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    gerente = await _usuario(usuarios, PerfilUsuario.GERENTE)
    os, estoque = await _os(ordens, estoques, mecanico)

    iniciada = await iniciar.executar(os.id, gerente.id)

    assert iniciada.status is StatusOS.EM_EXECUCAO
    assert estoque.quantidade_fisica == 3


async def test_outro_mecanico_nao_inicia_e_o_estoque_fica_intacto(
    iniciar, ordens, usuarios, estoques
):
    atribuido = await _usuario(usuarios, PerfilUsuario.MECANICO)
    outro = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os, estoque = await _os(ordens, estoques, atribuido)

    with pytest.raises(AcessoNegado):
        await iniciar.executar(os.id, outro.id)

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO
    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (5, 2)


async def test_usuario_desativado_nao_inicia(iniciar, ordens, usuarios, estoques):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO, ativo=False)
    os, estoque = await _os(ordens, estoques, mecanico)

    with pytest.raises(AcessoNegado):
        await iniciar.executar(os.id, mecanico.id)

    assert estoque.quantidade_reservada == 2


@pytest.mark.parametrize(
    "status",
    [StatusOS.AGUARDANDO_APROVACAO, StatusOS.AGUARDANDO_PECA, StatusOS.EM_EXECUCAO],
)
async def test_so_inicia_a_partir_de_aguardando_execucao(
    iniciar, ordens, usuarios, estoques, status
):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os, estoque = await _os(ordens, estoques, mecanico, status=status)

    with pytest.raises(TransicaoDeStatusInvalida):
        await iniciar.executar(os.id, mecanico.id)

    assert os.status is status
    assert estoque.quantidade_fisica == 5


async def test_os_inexistente(iniciar, usuarios):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)

    with pytest.raises(EntidadeNaoEncontrada):
        await iniciar.executar(uuid4(), mecanico.id)


async def test_usuario_inexistente(iniciar, ordens, usuarios, estoques):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os, _ = await _os(ordens, estoques, mecanico)

    with pytest.raises(EntidadeNaoEncontrada):
        await iniciar.executar(os.id, uuid4())


async def test_falha_da_baixa_sobe_para_a_unidade_de_trabalho(ordens, usuarios, estoques):
    class HandlerQueFalha(EventHandler):
        async def tratar(self, evento):
            raise RuntimeError("falha na baixa")

    despachador = EventDispatcher()
    despachador.registrar(ExecucaoIniciadaEvent, HandlerQueFalha())
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os, _ = await _os(ordens, estoques, mecanico)

    with pytest.raises(RuntimeError):
        await IniciarExecucao(ordens, usuarios, despachador).executar(os.id, mecanico.id)
