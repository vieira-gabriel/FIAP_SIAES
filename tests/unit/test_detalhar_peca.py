import pytest

from application.use_cases.cadastrar_peca import CadastrarPeca
from application.use_cases.detalhar_peca import DetalharPeca
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.valor import Valor


async def test_detalha_a_peca_com_o_estoque(pecas, estoques):
    peca, estoque = await CadastrarPeca(pecas, estoques).executar(
        "FLT-001", "Filtro de óleo", Valor("35.90"), 3, quantidade_fisica_inicial=4
    )

    assert await DetalharPeca(pecas, estoques).executar(peca.id) == (peca, estoque)


async def test_peca_excluida_nao_e_encontrada(pecas, estoques):
    peca, _ = await CadastrarPeca(pecas, estoques).executar(
        "FLT-001", "Filtro de óleo", Valor("35.90"), 3
    )
    peca.excluir([])

    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharPeca(pecas, estoques).executar(peca.id)
