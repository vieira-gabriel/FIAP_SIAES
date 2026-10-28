import pytest

from domain.entities.item_peca import ItemPeca
from domain.entities.peca import Peca
from domain.exceptions import OrdemServicoInvalida, ValorInvalido
from domain.value_objects.valor import Valor


def criar_peca(**alteracoes) -> Peca:
    dados = {
        "codigo_referencia": "FO-1234",
        "nome": "Filtro de óleo",
        "preco_unitario": Valor("35.90"),
        "prazo_reposicao_dias": 3,
    }
    dados.update(alteracoes)
    return Peca(**dados)


def reajustar(peca: Peca, preco: str, prazo: int) -> None:
    peca.atualizar_dados(
        codigo_referencia=peca.codigo_referencia,
        nome=peca.nome,
        preco_unitario=Valor(preco),
        prazo_reposicao_dias=prazo,
    )


def test_copia_nome_preco_e_prazo_do_catalogo_com_reserva_e_pendencia_zeradas():
    peca = criar_peca()

    item = ItemPeca.a_partir_de(peca, quantidade=2)

    assert item.peca_id == peca.id
    assert item.nome == "Filtro de óleo"
    assert item.quantidade == 2
    assert item.preco_unitario_congelado == Valor("35.90")
    assert item.prazo_reposicao_dias == 3
    assert (item.quantidade_reservada, item.quantidade_pendente) == (0, 0)


def test_valor_total_e_quantidade_vezes_preco_unitario():
    item = ItemPeca.a_partir_de(criar_peca(), quantidade=3)

    assert item.valor_total() == Valor("107.70")


@pytest.mark.parametrize("quantidade", [0, -1, 1.0, "2", True, None])
def test_recusa_quantidade_que_nao_e_inteiro_positivo(quantidade):
    with pytest.raises(OrdemServicoInvalida) as erro:
        ItemPeca.a_partir_de(criar_peca(), quantidade=quantidade)

    assert isinstance(erro.value, ValorInvalido)


@pytest.mark.parametrize(
    ("reservada", "pendente"),
    [(-1, 0), (0, -1), (1.0, 0), (0, "1"), (3, 2), (5, 0), (0, 5)],
)
def test_recusa_reservada_e_pendente_invalidas(reservada, pendente):
    with pytest.raises(OrdemServicoInvalida):
        ItemPeca(
            peca_id=criar_peca().id,
            nome="Filtro de óleo",
            quantidade=4,
            preco_unitario_congelado=Valor("35.90"),
            prazo_reposicao_dias=3,
            quantidade_reservada=reservada,
            quantidade_pendente=pendente,
        )


def test_aceita_reservada_mais_pendente_igual_a_quantidade():
    item = ItemPeca(
        peca_id=criar_peca().id,
        nome="Filtro de óleo",
        quantidade=4,
        preco_unitario_congelado=Valor("35.90"),
        prazo_reposicao_dias=3,
        quantidade_reservada=3,
        quantidade_pendente=1,
    )

    assert (item.quantidade_reservada, item.quantidade_pendente) == (3, 1)


def test_reajuste_do_catalogo_nao_altera_o_item():
    peca = criar_peca()
    item = ItemPeca.a_partir_de(peca, quantidade=2)

    reajustar(peca, "50.00", 10)

    assert item.preco_unitario_congelado == Valor("35.90")
    assert item.prazo_reposicao_dias == 3


def test_marcar_como_pendente_deixa_toda_a_quantidade_pendente_e_nada_reservado():
    item = ItemPeca.a_partir_de(criar_peca(), quantidade=4)
    item.quantidade_reservada = 3
    item.quantidade_pendente = 1

    item.marcar_como_pendente()

    assert (item.quantidade_reservada, item.quantidade_pendente) == (0, 4)


def test_descartar_pendencia_zera_a_pendente_e_mantem_a_reservada():
    item = ItemPeca.a_partir_de(criar_peca(), quantidade=4)
    item.quantidade_reservada = 3
    item.quantidade_pendente = 1

    item.descartar_pendencia()

    assert (item.quantidade_reservada, item.quantidade_pendente) == (3, 0)


def test_congelar_atualiza_com_os_valores_vigentes_do_catalogo():
    peca = criar_peca()
    item = ItemPeca.a_partir_de(peca, quantidade=2)
    reajustar(peca, "50.00", 10)

    item.congelar(peca)

    assert item.preco_unitario_congelado == Valor("50.00")
    assert item.prazo_reposicao_dias == 10
    assert item.valor_total() == Valor("100.00")
    assert item.quantidade == 2


def test_congelar_recusa_peca_diferente_do_item():
    item = ItemPeca.a_partir_de(criar_peca(), quantidade=1)

    with pytest.raises(OrdemServicoInvalida):
        item.congelar(criar_peca())


def test_igualdade_pela_peca_do_catalogo():
    peca = criar_peca()

    assert ItemPeca.a_partir_de(peca, 1) == ItemPeca.a_partir_de(peca, 5)
    assert ItemPeca.a_partir_de(peca, 1) != ItemPeca.a_partir_de(criar_peca(), 1)
    assert len({ItemPeca.a_partir_de(peca, 1), ItemPeca.a_partir_de(peca, 2)}) == 1
