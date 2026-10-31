from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.use_cases.aprovar_orcamento import AprovarOrcamento
from application.use_cases.localizar_os_do_titular import LocalizarOSDoTitular
from domain.entities.cliente import Cliente
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada, TransicaoDeStatusInvalida
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

MOMENTO = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
NUMERO = "529-7F3A9C2B"
DOCUMENTO = "529.982.247-25"


@pytest.fixture
def aprovar(ordens, clientes) -> AprovarOrcamento:
    return AprovarOrcamento(LocalizarOSDoTitular(ordens, clientes), ordens)


def _peca(quantidade: int, pendente: int) -> ItemPeca:
    return ItemPeca(
        peca_id=uuid4(),
        nome="Filtro de óleo",
        quantidade=quantidade,
        preco_unitario_congelado=Valor("35.90"),
        prazo_reposicao_dias=3,
        quantidade_reservada=quantidade - pendente,
        quantidade_pendente=pendente,
    )


async def _os(clientes, ordens, status=StatusOS.AGUARDANDO_APROVACAO, pecas=()) -> OrdemServico:
    cliente = Cliente(nome="Maria", documento=CPF("52998224725"), email="m@e.com", telefone="11")
    await clientes.salvar(cliente)
    os = OrdemServico(
        numero=NumeroOS(NUMERO),
        cliente_id=cliente.id,
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=status,
        pecas=list(pecas),
    )
    await ordens.salvar(os)
    return os


async def test_aprovacao_sem_pendencia_aguarda_a_execucao(aprovar, clientes, ordens):
    os = await _os(clientes, ordens, pecas=[_peca(2, pendente=0)])

    acompanhamento = await aprovar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert acompanhamento.os is os
    assert os.status is StatusOS.AGUARDANDO_EXECUCAO
    assert acompanhamento.estimativa_entrega is not None


async def test_aprovacao_com_pendencia_aguarda_a_peca(aprovar, clientes, ordens):
    os = await _os(clientes, ordens, pecas=[_peca(2, pendente=2)])

    await aprovar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert os.status is StatusOS.AGUARDANDO_PECA


async def test_aprovacao_grava_a_origem_cliente_sem_usuario_no_historico(aprovar, clientes, ordens):
    os = await _os(clientes, ordens)

    await aprovar.executar(NUMERO, DOCUMENTO, MOMENTO)

    registro = os.historico[-1]
    assert (registro.status_anterior, registro.origem, registro.usuario_id) == (
        StatusOS.AGUARDANDO_APROVACAO,
        OrigemTransicao.CLIENTE,
        None,
    )


async def test_aprovacao_e_salva(aprovar, clientes, ordens):
    os = await _os(clientes, ordens)

    await aprovar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert (await ordens.buscar_por_id(os.id)).status is StatusOS.AGUARDANDO_EXECUCAO


@pytest.mark.parametrize(
    "status",
    [
        StatusOS.RECEBIDA,
        StatusOS.EM_DIAGNOSTICO,
        StatusOS.AGUARDANDO_PECA,
        StatusOS.AGUARDANDO_EXECUCAO,
        StatusOS.EM_EXECUCAO,
        StatusOS.FINALIZADA,
        StatusOS.ENTREGUE,
        StatusOS.CANCELADA,
    ],
)
async def test_aprovacao_fora_de_aguardando_aprovacao_e_recusada(aprovar, clientes, ordens, status):
    os = await _os(clientes, ordens, status=status)

    with pytest.raises(TransicaoDeStatusInvalida):
        await aprovar.executar(NUMERO, DOCUMENTO, MOMENTO)

    assert os.status is status


@pytest.mark.parametrize(
    ("numero", "documento"),
    [("999-00000000", DOCUMENTO), (NUMERO, "111.444.777-35"), (NUMERO, "lixo")],
    ids=["numero inexistente", "documento de outro titular", "documento malformado"],
)
async def test_identificacao_errada_nao_aprova(aprovar, clientes, ordens, numero, documento):
    os = await _os(clientes, ordens)

    with pytest.raises(EntidadeNaoEncontrada):
        await aprovar.executar(numero, documento, MOMENTO)

    assert os.status is StatusOS.AGUARDANDO_APROVACAO
