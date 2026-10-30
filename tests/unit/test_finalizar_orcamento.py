from uuid import UUID, uuid4

import pytest

from application.events.event_dispatcher import EventDispatcher, EventHandler
from application.use_cases.finalizar_orcamento import FinalizarOrcamento
from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.exceptions import EntidadeNaoEncontrada, ItemIndisponivel
from domain.repositories.estoque_repository import EstoqueRepository
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

USUARIO_ID = uuid4()


class EstoquesQueRegistramOBloqueio(EstoqueRepository):
    def __init__(self):
        self.bloqueados: list[UUID] = []

    async def salvar(self, estoque):
        raise NotImplementedError

    async def buscar_por_peca(self, peca_id):
        self.bloqueados.append(peca_id)

    async def buscar_por_pecas(self, peca_ids):
        raise NotImplementedError


def _peca(codigo: str) -> Peca:
    return Peca(
        codigo_referencia=codigo,
        nome=f"Peça {codigo}",
        preco_unitario=Valor("10.00"),
        prazo_reposicao_dias=2,
    )


@pytest.fixture
def estoques():
    return EstoquesQueRegistramOBloqueio()


class HandlerQueFalha(EventHandler):
    async def tratar(self, evento):
        raise RuntimeError("falha na reserva")


@pytest.fixture
def despachador(orcamentos_finalizados) -> EventDispatcher:
    despachador = EventDispatcher()
    despachador.registrar(OrcamentoFinalizadoEvent, orcamentos_finalizados)
    return despachador


@pytest.fixture
def finalizar(ordens, estoques, servicos, pecas, despachador):
    return FinalizarOrcamento(ordens, estoques, servicos, pecas, despachador)


async def _os_em_diagnostico(ordens, servicos_da_os=(), pecas_da_os=()) -> OrdemServico:
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=StatusOS.EM_DIAGNOSTICO,
    )
    for servico in servicos_da_os:
        os.incluir_servico(servico)
    for peca in pecas_da_os:
        os.incluir_peca(peca, quantidade=1)
    await ordens.salvar(os)
    return os


async def test_congela_os_valores_vigentes_e_aguarda_a_aprovacao(
    finalizar, ordens, servicos, pecas
):
    servico = Servico(
        codigo="SRV-001",
        nome="Troca de óleo",
        descricao="Troca do óleo",
        valor_base=Valor("100.00"),
        tempo_estimado_minutos=30,
    )
    peca = _peca("FLT-001")
    await servicos.salvar(servico)
    await pecas.salvar(peca)
    os = await _os_em_diagnostico(ordens, [servico], [peca])

    await finalizar.executar(os.id, USUARIO_ID)

    salva = await ordens.buscar_por_id(os.id)
    assert salva.status is StatusOS.AGUARDANDO_APROVACAO
    assert salva.orcamento.total == Valor("110.00")
    assert salva.historico[-1].usuario_id == USUARIO_ID


async def test_bloqueia_o_estoque_de_cada_peca_em_ordem_de_id(finalizar, ordens, pecas, estoques):
    itens = [_peca("FLT-001"), _peca("VEL-001"), _peca("PST-001")]
    for peca in itens:
        await pecas.salvar(peca)
    os = await _os_em_diagnostico(ordens, pecas_da_os=itens)

    await finalizar.executar(os.id, USUARIO_ID)

    assert estoques.bloqueados == sorted(peca.id for peca in itens)


async def test_peca_excluida_depois_de_incluida_mantem_a_os_em_diagnostico(
    finalizar, ordens, pecas
):
    peca = _peca("FLT-001")
    os = await _os_em_diagnostico(ordens, pecas_da_os=[peca])
    peca.excluir([])
    await pecas.salvar(peca)

    with pytest.raises(ItemIndisponivel):
        await finalizar.executar(os.id, USUARIO_ID)

    assert (await ordens.buscar_por_id(os.id)).status is StatusOS.EM_DIAGNOSTICO


async def test_os_inexistente(finalizar):
    with pytest.raises(EntidadeNaoEncontrada):
        await finalizar.executar(uuid4(), USUARIO_ID)


async def test_despacha_o_orcamento_finalizado_depois_de_salvar_a_os(
    finalizar, ordens, orcamentos_finalizados
):
    os = await _os_em_diagnostico(ordens)

    await finalizar.executar(os.id, USUARIO_ID)

    (evento,) = orcamentos_finalizados.recebidos
    assert isinstance(evento, OrcamentoFinalizadoEvent)
    assert evento.os_id == os.id
    assert (await ordens.buscar_por_id(os.id)).collect_domain_events() == []


async def test_conclusao_recusada_nao_despacha_evento(finalizar, ordens, orcamentos_finalizados):
    peca = _peca("FLT-001")
    os = await _os_em_diagnostico(ordens, pecas_da_os=[peca])
    peca.excluir([])

    with pytest.raises(ItemIndisponivel):
        await finalizar.executar(os.id, USUARIO_ID)

    assert orcamentos_finalizados.recebidos == []


async def test_falha_do_handler_sobe_para_a_unidade_de_trabalho_desfazer(
    ordens, estoques, servicos, pecas
):
    despachador = EventDispatcher()
    despachador.registrar(OrcamentoFinalizadoEvent, HandlerQueFalha())
    finalizar = FinalizarOrcamento(ordens, estoques, servicos, pecas, despachador)
    os = await _os_em_diagnostico(ordens)

    with pytest.raises(RuntimeError, match="falha na reserva"):
        await finalizar.executar(os.id, USUARIO_ID)
