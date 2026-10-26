import pytest

from domain.entities.peca import Peca
from domain.exceptions import PecaInvalida, ValorInvalido
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


def test_cria_peca_ativa_e_disponivel_para_os():
    peca = criar_peca()

    assert peca.ativo
    assert peca.pode_ser_incluida_em_os()
    assert peca.id is not None


def test_guarda_so_o_cadastro_sem_quantidades():
    assert not any("quantidade" in campo for campo in vars(criar_peca()))


def test_normaliza_textos():
    peca = criar_peca(codigo_referencia=" FO-1234 ", nome=" Filtro de óleo ")

    assert (peca.codigo_referencia, peca.nome) == ("FO-1234", "Filtro de óleo")


@pytest.mark.parametrize("dias", [0, 1, 30])
def test_aceita_prazo_de_reposicao_nao_negativo(dias):
    assert criar_peca(prazo_reposicao_dias=dias).prazo_reposicao_dias == dias


@pytest.mark.parametrize(
    "alteracao",
    [
        {"codigo_referencia": " "},
        {"nome": ""},
        {"preco_unitario": "35.90"},
        {"prazo_reposicao_dias": -1},
        {"prazo_reposicao_dias": 3.0},
        {"prazo_reposicao_dias": "3"},
        {"prazo_reposicao_dias": False},
    ],
)
def test_rejeita_dados_invalidos(alteracao):
    with pytest.raises(PecaInvalida) as erro:
        criar_peca(**alteracao)

    assert isinstance(erro.value, ValorInvalido)


def test_altera_preco_e_prazo_de_reposicao():
    peca = criar_peca()

    peca.atualizar_dados(
        codigo_referencia="FO-1234",
        nome="Filtro de óleo",
        preco_unitario=Valor("39.90"),
        prazo_reposicao_dias=5,
    )

    assert peca.preco_unitario == Valor("39.90")
    assert peca.prazo_reposicao_dias == 5


def test_alteracao_invalida_nao_altera_nenhum_dado():
    peca = criar_peca()

    with pytest.raises(PecaInvalida):
        peca.atualizar_dados(
            codigo_referencia="FO-9999",
            nome="Outro",
            preco_unitario=Valor("39.90"),
            prazo_reposicao_dias=-2,
        )

    assert peca.codigo_referencia == "FO-1234"
    assert peca.preco_unitario == Valor("35.90")
    assert peca.prazo_reposicao_dias == 3


def test_peca_excluida_nao_pode_ser_incluida_em_os():
    peca = criar_peca()

    peca.excluir()

    assert not peca.ativo
    assert not peca.pode_ser_incluida_em_os()
    assert peca.nome == "Filtro de óleo"


def test_igualdade_pela_identidade():
    peca = criar_peca()

    assert peca != criar_peca()
    assert peca == criar_peca(id=peca.id, nome="Outro nome")
    assert len({peca, criar_peca()}) == 2
