from uuid import uuid4

import pytest

from application.use_cases.entregar_veiculo import EntregarVeiculo
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada, TransicaoDeStatusInvalida
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS

ATENDENTE_ID = uuid4()


@pytest.fixture
def entregar(ordens) -> EntregarVeiculo:
    return EntregarVeiculo(ordens)


async def _os(ordens, status=StatusOS.FINALIZADA) -> OrdemServico:
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=status,
    )
    await ordens.salvar(os)
    return os


async def test_entrega_a_os_finalizada_e_registra_o_usuario_no_historico(entregar, ordens):
    os = await _os(ordens)

    entregue = await entregar.executar(os.id, ATENDENTE_ID)

    assert entregue.status is StatusOS.ENTREGUE
    registro = entregue.historico[-1]
    assert (registro.status_anterior, registro.status_novo, registro.usuario_id) == (
        StatusOS.FINALIZADA,
        StatusOS.ENTREGUE,
        ATENDENTE_ID,
    )
    assert (await ordens.buscar_por_id(os.id)).status is StatusOS.ENTREGUE


@pytest.mark.parametrize(
    "status",
    [
        StatusOS.EM_DIAGNOSTICO,
        StatusOS.AGUARDANDO_EXECUCAO,
        StatusOS.EM_EXECUCAO,
        StatusOS.ENTREGUE,
        StatusOS.CANCELADA,
    ],
)
async def test_so_entrega_a_partir_de_finalizada(entregar, ordens, status):
    os = await _os(ordens, status=status)

    with pytest.raises(TransicaoDeStatusInvalida):
        await entregar.executar(os.id, ATENDENTE_ID)

    assert os.status is status


async def test_os_inexistente(entregar):
    with pytest.raises(EntidadeNaoEncontrada):
        await entregar.executar(uuid4(), ATENDENTE_ID)
