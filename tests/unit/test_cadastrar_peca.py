import pytest

from application.use_cases.cadastrar_peca import CadastrarPeca
from domain.exceptions import CodigoDePecaJaCadastrado, PecaInvalida, QuantidadeInvalida
from domain.value_objects.valor import Valor


def _cadastrar(pecas, estoques, codigo="FLT-001", **extras):
    return CadastrarPeca(pecas, estoques).executar(
        codigo, "Filtro de óleo", Valor("35.90"), 3, **extras
    )


async def test_cadastra_a_peca_com_estoque_zerado(pecas, estoques):
    peca, estoque = await _cadastrar(pecas, estoques)

    assert await pecas.buscar_por_id(peca.id) == peca
    assert await estoques.buscar_por_peca(peca.id) == estoque
    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (0, 0)


async def test_cadastra_com_quantidade_inicial_sem_emitir_evento(pecas, estoques):
    _, estoque = await _cadastrar(pecas, estoques, quantidade_fisica_inicial=12)

    assert estoque.saldo_disponivel() == 12
    assert estoque.collect_domain_events() == []


async def test_recusa_codigo_ja_usado_por_outra_peca(pecas, estoques):
    await _cadastrar(pecas, estoques)

    with pytest.raises(CodigoDePecaJaCadastrado):
        await _cadastrar(pecas, estoques)

    assert len(pecas.dados) == len(estoques.dados) == 1


@pytest.mark.parametrize(
    ("dados", "erro"),
    [
        ({"quantidade_fisica_inicial": -1}, QuantidadeInvalida),
        ({"codigo": " "}, PecaInvalida),
    ],
)
async def test_dados_invalidos_nao_gravam_nada(pecas, estoques, dados, erro):
    with pytest.raises(erro):
        await _cadastrar(pecas, estoques, **dados)

    assert pecas.dados == estoques.dados == {}
