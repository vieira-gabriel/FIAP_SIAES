from uuid import uuid4

import pytest

from domain.entities.servico import Servico
from domain.exceptions import CodigoDeServicoJaCadastrado, EntidadeNaoEncontrada
from domain.repositories.servico_repository import ServicoRepository
from domain.value_objects.valor import Valor


def _servico(codigo="SRV-001", nome="Troca de óleo"):
    return Servico(
        codigo=codigo,
        nome=nome,
        descricao="Troca do óleo e do filtro",
        valor_base=Valor("120.00"),
        tempo_estimado_minutos=45,
    )


def test_porta_define_salvar_buscas_e_listagem():
    assert ServicoRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_codigo",
        "listar",
    }


async def test_buscar_ativo_por_id_devolve_o_servico_ativo(servicos):
    servico = _servico()
    await servicos.salvar(servico)

    assert await servicos.buscar_ativo_por_id(servico.id) == servico


async def test_buscar_ativo_por_id_trata_o_servico_excluido_como_inexistente(servicos):
    servico = _servico()
    servico.excluir()
    await servicos.salvar(servico)

    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await servicos.buscar_ativo_por_id(servico.id)

    assert erro.value.entidade == "Serviço"


async def test_buscar_ativo_por_id_inexistente(servicos):
    with pytest.raises(EntidadeNaoEncontrada):
        await servicos.buscar_ativo_por_id(uuid4())


async def test_codigo_de_outro_servico_nao_esta_livre_mesmo_excluido(servicos):
    excluido = _servico()
    excluido.excluir()
    await servicos.salvar(excluido)

    with pytest.raises(CodigoDeServicoJaCadastrado) as erro:
        await servicos.garantir_codigo_livre(_servico(nome="Outro serviço"))

    assert erro.value.codigo == "SRV-001"


async def test_o_proprio_codigo_continua_livre_para_o_dono(servicos):
    servico = _servico()
    await servicos.salvar(servico)

    await servicos.garantir_codigo_livre(servico)
