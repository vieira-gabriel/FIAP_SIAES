from uuid import uuid4

import pytest

from domain.entities.peca import Peca
from domain.exceptions import CodigoDePecaJaCadastrado, EntidadeNaoEncontrada
from domain.repositories.peca_repository import PecaRepository
from domain.value_objects.valor import Valor


def criar_peca(codigo_referencia="FLT-001", nome="Filtro de óleo"):
    return Peca(
        codigo_referencia=codigo_referencia,
        nome=nome,
        preco_unitario=Valor("35.00"),
        prazo_reposicao_dias=3,
    )


def test_porta_define_salvar_buscas_e_listagem():
    assert PecaRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_codigo_referencia",
        "listar",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemListagem(PecaRepository):
        async def salvar(self, peca): ...

        async def buscar_por_id(self, id): ...

        async def buscar_por_codigo_referencia(self, codigo_referencia): ...

    with pytest.raises(TypeError):
        SemListagem()


async def test_salva_e_busca_a_peca_pelo_id_e_pelo_codigo_mesmo_excluida(pecas):
    peca = criar_peca()
    peca.excluir([])
    await pecas.salvar(peca)

    assert await pecas.buscar_por_id(peca.id) == peca
    assert await pecas.buscar_por_codigo_referencia("FLT-001") == peca
    assert await pecas.buscar_por_id(uuid4()) is None
    assert await pecas.buscar_por_codigo_referencia("XXX-999") is None


async def test_lista_so_as_ativas_em_ordem_de_nome(pecas):
    vela = criar_peca("VEL-001", "Vela de ignição")
    filtro = criar_peca("FLT-001", "Filtro de óleo")
    excluida = criar_peca("PAS-001", "Pastilha de freio")
    excluida.excluir([])
    for peca in (vela, excluida, filtro):
        await pecas.salvar(peca)

    assert await pecas.listar() == [filtro, vela]


async def test_buscar_ativa_por_id_devolve_a_peca_ativa(pecas):
    peca = criar_peca()
    await pecas.salvar(peca)

    assert await pecas.buscar_ativa_por_id(peca.id) == peca


async def test_buscar_ativa_por_id_trata_a_peca_excluida_como_inexistente(pecas):
    peca = criar_peca()
    peca.excluir([])
    await pecas.salvar(peca)

    with pytest.raises(EntidadeNaoEncontrada):
        await pecas.buscar_ativa_por_id(peca.id)
    with pytest.raises(EntidadeNaoEncontrada):
        await pecas.buscar_ativa_por_id(uuid4())


async def test_garantir_codigo_livre_aceita_a_propria_peca(pecas):
    peca = criar_peca()
    await pecas.salvar(peca)

    await pecas.garantir_codigo_livre(peca)


async def test_garantir_codigo_livre_recusa_o_codigo_de_outra_peca_mesmo_excluida(pecas):
    excluida = criar_peca("FLT-001")
    excluida.excluir([])
    await pecas.salvar(excluida)

    with pytest.raises(CodigoDePecaJaCadastrado):
        await pecas.garantir_codigo_livre(criar_peca("FLT-001", "Outro filtro"))
