import pytest

from application.use_cases.excluir_servico import ExcluirServico
from domain.entities.servico import Servico
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.valor import Valor


def _servico():
    return Servico(
        codigo="SRV-001",
        nome="Troca de óleo",
        descricao="Troca do óleo e do filtro",
        valor_base=Valor("120"),
        tempo_estimado_minutos=45,
    )


async def test_exclusao_logica_tira_o_servico_das_novas_os(servicos):
    servico = _servico()
    await servicos.salvar(servico)

    await ExcluirServico(servicos).executar(servico.id)

    salvo = await servicos.buscar_por_id(servico.id)
    assert salvo is not None
    assert not salvo.ativo
    assert not salvo.pode_ser_incluido_em_os()


async def test_excluir_de_novo_nao_encontra_o_servico(servicos):
    servico = _servico()
    await servicos.salvar(servico)
    await ExcluirServico(servicos).executar(servico.id)

    with pytest.raises(EntidadeNaoEncontrada):
        await ExcluirServico(servicos).executar(servico.id)
