import pytest

from application.use_cases.cadastrar_servico import CadastrarServico
from domain.exceptions import CodigoDeServicoJaCadastrado, ServicoInvalido
from domain.value_objects.valor import Valor


async def test_cadastra_servico_ativo_no_catalogo(servicos):
    servico = await CadastrarServico(servicos).executar(
        "SRV-001", "Troca de óleo", "Troca do óleo e do filtro", Valor("120.00"), 45
    )

    salvo = await servicos.buscar_por_id(servico.id)
    assert (salvo.codigo, salvo.valor_base, salvo.tempo_estimado_minutos) == (
        "SRV-001",
        Valor("120.00"),
        45,
    )
    assert salvo.ativo


async def test_recusa_codigo_ja_cadastrado(servicos):
    cadastrar = CadastrarServico(servicos)
    await cadastrar.executar("SRV-001", "Troca de óleo", "Troca", Valor("120"), 45)

    with pytest.raises(CodigoDeServicoJaCadastrado):
        await cadastrar.executar("SRV-001", "Alinhamento", "Alinhamento", Valor("80"), 30)

    assert len(servicos.dados) == 1


async def test_recusa_codigo_de_servico_excluido(servicos):
    cadastrar = CadastrarServico(servicos)
    excluido = await cadastrar.executar("SRV-001", "Troca de óleo", "Troca", Valor("120"), 45)
    excluido.excluir()

    with pytest.raises(CodigoDeServicoJaCadastrado):
        await cadastrar.executar("SRV-001", "Troca nova", "Troca", Valor("130"), 45)


async def test_tempo_estimado_negativo_nao_grava_nada(servicos):
    with pytest.raises(ServicoInvalido):
        await CadastrarServico(servicos).executar(
            "SRV-001", "Troca de óleo", "Troca", Valor("120"), -1
        )

    assert servicos.dados == {}
