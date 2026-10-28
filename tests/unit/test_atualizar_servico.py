from uuid import uuid4

import pytest

from application.use_cases.atualizar_servico import AtualizarServico
from domain.entities.servico import Servico
from domain.exceptions import (
    CodigoDeServicoJaCadastrado,
    EntidadeNaoEncontrada,
    ServicoInvalido,
)
from domain.value_objects.valor import Valor


def _servico(codigo="SRV-001", nome="Troca de óleo"):
    return Servico(
        codigo=codigo,
        nome=nome,
        descricao="Troca do óleo e do filtro",
        valor_base=Valor("120.00"),
        tempo_estimado_minutos=45,
    )


async def test_altera_preco_e_tempo_estimado(servicos):
    servico = _servico()
    await servicos.salvar(servico)

    await AtualizarServico(servicos).executar(
        servico.id, "SRV-001", "Troca de óleo", "Troca do óleo e do filtro", Valor("150.00"), 60
    )

    salvo = await servicos.buscar_por_id(servico.id)
    assert (salvo.valor_base, salvo.tempo_estimado_minutos) == (Valor("150.00"), 60)


async def test_recusa_codigo_de_outro_servico(servicos):
    oleo, alinhamento = _servico(), _servico(codigo="SRV-002", nome="Alinhamento")
    await servicos.salvar(oleo)
    await servicos.salvar(alinhamento)

    with pytest.raises(CodigoDeServicoJaCadastrado):
        await AtualizarServico(servicos).executar(
            alinhamento.id, "SRV-001", "Alinhamento", "Alinhamento", Valor("80"), 30
        )


async def test_servico_excluido_nao_e_encontrado(servicos):
    servico = _servico()
    servico.excluir()
    await servicos.salvar(servico)

    with pytest.raises(EntidadeNaoEncontrada):
        await AtualizarServico(servicos).executar(
            servico.id, "SRV-001", "Troca", "Troca", Valor("120"), 45
        )


async def test_servico_inexistente(servicos):
    with pytest.raises(EntidadeNaoEncontrada):
        await AtualizarServico(servicos).executar(
            uuid4(), "SRV-001", "Troca", "Troca", Valor("120"), 45
        )


async def test_dados_invalidos_nao_alteram_o_servico(servicos):
    servico = _servico()
    await servicos.salvar(servico)

    with pytest.raises(ServicoInvalido):
        await AtualizarServico(servicos).executar(
            servico.id, "SRV-001", "Troca de óleo", "", Valor("150"), 60
        )

    assert (await servicos.buscar_por_id(servico.id)).valor_base == Valor("120.00")
