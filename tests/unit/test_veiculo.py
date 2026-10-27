from datetime import date
from uuid import uuid4

import pytest

from domain.entities.veiculo import ANO_MINIMO, Veiculo
from domain.exceptions import ValorInvalido, VeiculoInvalido
from domain.value_objects.placa import Placa

PROXIMO_ANO = date.today().year + 1


def criar_veiculo(**alteracoes) -> Veiculo:
    dados = {
        "cliente_id": uuid4(),
        "placa": Placa("ABC1D23"),
        "marca": "Fiat",
        "modelo": "Uno",
        "ano": 2015,
    }
    dados.update(alteracoes)
    return Veiculo(**dados)


def test_cria_veiculo_ativo_vinculado_ao_cliente():
    cliente_id = uuid4()

    veiculo = criar_veiculo(cliente_id=cliente_id)

    assert veiculo.ativo
    assert veiculo.cliente_id == cliente_id
    assert veiculo.id is not None


def test_normaliza_marca_e_modelo():
    veiculo = criar_veiculo(marca="  Fiat ", modelo=" Uno  ")

    assert (veiculo.marca, veiculo.modelo) == ("Fiat", "Uno")


@pytest.mark.parametrize("ano", [ANO_MINIMO, 2015, PROXIMO_ANO])
def test_aceita_ano_dentro_da_faixa(ano):
    assert criar_veiculo(ano=ano).ano == ano


@pytest.mark.parametrize(
    "alteracao",
    [
        {"cliente_id": "nao-e-uuid"},
        {"placa": "ABC1D23"},
        {"marca": " "},
        {"modelo": ""},
        {"ano": ANO_MINIMO - 1},
        {"ano": PROXIMO_ANO + 1},
        {"ano": "2015"},
        {"ano": 2015.0},
        {"ano": True},
    ],
)
def test_rejeita_dados_invalidos(alteracao):
    with pytest.raises(VeiculoInvalido) as erro:
        criar_veiculo(**alteracao)

    assert isinstance(erro.value, ValorInvalido)


def test_atualizar_dados():
    veiculo = criar_veiculo()

    veiculo.atualizar_dados(placa=Placa("XYZ9876"), marca="VW", modelo="Gol", ano=2020)

    assert veiculo.placa == Placa("XYZ9876")
    assert (veiculo.marca, veiculo.modelo, veiculo.ano) == ("VW", "Gol", 2020)


def test_atualizacao_invalida_nao_altera_nenhum_dado():
    veiculo = criar_veiculo()

    with pytest.raises(VeiculoInvalido):
        veiculo.atualizar_dados(placa=Placa("XYZ9876"), marca="VW", modelo="Gol", ano=1800)

    assert veiculo.placa == Placa("ABC1D23")
    assert (veiculo.marca, veiculo.modelo, veiculo.ano) == ("Fiat", "Uno", 2015)


def test_exclusao_logica_mantem_os_dados():
    veiculo = criar_veiculo()

    veiculo.excluir()

    assert not veiculo.ativo
    assert veiculo.placa == Placa("ABC1D23")


def test_igualdade_pela_identidade():
    veiculo = criar_veiculo()

    assert veiculo != criar_veiculo()
    assert veiculo == criar_veiculo(id=veiculo.id, modelo="Outro")
    assert len({veiculo, criar_veiculo()}) == 2
