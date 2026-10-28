import pytest

from application.use_cases.ajustar_quantidade_fisica_da_peca import AjustarQuantidadeFisicaDaPeca
from application.use_cases.cadastrar_peca import CadastrarPeca
from domain.exceptions import EntidadeNaoEncontrada, SaldoInsuficiente
from domain.value_objects.valor import Valor


async def _cadastrar_com_reserva(pecas, estoques):
    peca, estoque = await CadastrarPeca(pecas, estoques).executar(
        "FLT-001", "Filtro de óleo", Valor("35.90"), 3, quantidade_fisica_inicial=5
    )
    estoque.reservar(3)
    return peca


def _ajustar(pecas, estoques, eventos):
    return AjustarQuantidadeFisicaDaPeca(pecas, estoques, eventos)


async def test_aumento_despacha_o_saldo_atualizado(pecas, estoques, eventos, saldos_atualizados):
    peca = await _cadastrar_com_reserva(pecas, estoques)

    _, estoque = await _ajustar(pecas, estoques, eventos).executar(peca.id, 8)

    assert estoque.quantidade_fisica == 8
    assert [e.saldo_disponivel for e in saldos_atualizados.recebidos] == [5]


async def test_reducao_nao_despacha_evento(pecas, estoques, eventos, saldos_atualizados):
    peca = await _cadastrar_com_reserva(pecas, estoques)

    _, estoque = await _ajustar(pecas, estoques, eventos).executar(peca.id, 4)

    assert estoque.saldo_disponivel() == 1
    assert saldos_atualizados.recebidos == []


async def test_ajuste_abaixo_da_reserva_e_recusado(pecas, estoques, eventos, saldos_atualizados):
    peca = await _cadastrar_com_reserva(pecas, estoques)

    with pytest.raises(SaldoInsuficiente):
        await _ajustar(pecas, estoques, eventos).executar(peca.id, 2)

    assert (await estoques.buscar_por_peca(peca.id)).quantidade_fisica == 5
    assert saldos_atualizados.recebidos == []


async def test_peca_excluida_nao_e_ajustada(pecas, estoques, eventos):
    peca = await _cadastrar_com_reserva(pecas, estoques)
    peca.excluir([])

    with pytest.raises(EntidadeNaoEncontrada):
        await _ajustar(pecas, estoques, eventos).executar(peca.id, 9)
