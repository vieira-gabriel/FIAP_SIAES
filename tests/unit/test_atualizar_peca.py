from uuid import uuid4

import pytest

from application.use_cases.atualizar_peca import AtualizarPeca
from application.use_cases.cadastrar_peca import CadastrarPeca
from domain.exceptions import CodigoDePecaJaCadastrado, EntidadeNaoEncontrada
from domain.value_objects.valor import Valor


async def _cadastrar(pecas, estoques, codigo="FLT-001"):
    peca, _ = await CadastrarPeca(pecas, estoques).executar(
        codigo, "Filtro de óleo", Valor("35.90"), 3, quantidade_fisica_inicial=5
    )
    return peca


async def test_altera_os_dados_e_devolve_o_estoque(pecas, estoques):
    peca = await _cadastrar(pecas, estoques)

    alterada, estoque = await AtualizarPeca(pecas, estoques).executar(
        peca.id, "FLT-002", "Filtro de óleo sintético", Valor("42.00"), 5
    )

    salva = await pecas.buscar_por_id(peca.id)
    assert (salva.codigo_referencia, salva.preco_unitario, salva.prazo_reposicao_dias) == (
        "FLT-002",
        Valor("42.00"),
        5,
    )
    assert alterada == salva
    assert estoque.quantidade_fisica == 5


async def test_recusa_o_codigo_de_outra_peca(pecas, estoques):
    await _cadastrar(pecas, estoques, "FLT-001")
    vela = await _cadastrar(pecas, estoques, "VEL-001")

    with pytest.raises(CodigoDePecaJaCadastrado):
        await AtualizarPeca(pecas, estoques).executar(vela.id, "FLT-001", "Vela", Valor("20.00"), 2)


async def test_peca_excluida_ou_inexistente_nao_e_encontrada(pecas, estoques):
    peca = await _cadastrar(pecas, estoques)
    peca.excluir([])

    for id in (peca.id, uuid4()):
        with pytest.raises(EntidadeNaoEncontrada):
            await AtualizarPeca(pecas, estoques).executar(id, "X", "Y", Valor("1.00"), 1)
