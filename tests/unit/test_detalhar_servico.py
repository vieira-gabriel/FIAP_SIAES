from uuid import uuid4

import pytest

from application.use_cases.detalhar_servico import DetalharServico
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


async def test_detalha_servico_ativo(servicos):
    servico = _servico()
    await servicos.salvar(servico)

    assert await DetalharServico(servicos).executar(servico.id) == servico


async def test_servico_excluido_nao_e_encontrado(servicos):
    servico = _servico()
    servico.excluir()
    await servicos.salvar(servico)

    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharServico(servicos).executar(servico.id)


async def test_servico_inexistente(servicos):
    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharServico(servicos).executar(uuid4())
