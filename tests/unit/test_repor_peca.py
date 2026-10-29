import pytest

from application.use_cases.cadastrar_peca import CadastrarPeca
from application.use_cases.repor_peca import ReporPeca
from domain.exceptions import EntidadeNaoEncontrada, QuantidadeInvalida
from domain.value_objects.valor import Valor


async def _cadastrar(pecas, estoques):
    peca, _ = await CadastrarPeca(pecas, estoques).executar(
        "FLT-001", "Filtro de óleo", Valor("35.90"), 3, quantidade_fisica_inicial=2
    )
    return peca


async def test_repoe_e_despacha_o_saldo_atualizado(pecas, estoques, eventos, saldos_atualizados):
    peca = await _cadastrar(pecas, estoques)

    _, estoque = await ReporPeca(pecas, estoques, eventos).executar(peca.id, 5)

    assert (await estoques.buscar_por_peca(peca.id)).quantidade_fisica == 7
    assert [(e.peca_id, e.saldo_disponivel) for e in saldos_atualizados.recebidos] == [(peca.id, 7)]
    assert estoque.collect_domain_events() == []


async def test_quantidade_nao_positiva_nao_altera_nem_despacha(
    pecas, estoques, eventos, saldos_atualizados
):
    peca = await _cadastrar(pecas, estoques)

    with pytest.raises(QuantidadeInvalida):
        await ReporPeca(pecas, estoques, eventos).executar(peca.id, 0)

    assert (await estoques.buscar_por_peca(peca.id)).quantidade_fisica == 2
    assert saldos_atualizados.recebidos == []


async def test_peca_excluida_nao_e_reposta(pecas, estoques, eventos):
    peca = await _cadastrar(pecas, estoques)
    peca.excluir([])

    with pytest.raises(EntidadeNaoEncontrada):
        await ReporPeca(pecas, estoques, eventos).executar(peca.id, 5)
