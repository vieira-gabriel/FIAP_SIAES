import pytest

from domain.entities.servico import Servico
from domain.exceptions import ServicoInvalido, ValorInvalido
from domain.value_objects.valor import Valor


def criar_servico(**alteracoes) -> Servico:
    dados = {
        "codigo": "SRV-001",
        "nome": "Troca de óleo",
        "descricao": "Troca do óleo do motor e do filtro de óleo",
        "valor_base": Valor("120.00"),
        "tempo_estimado_minutos": 45,
    }
    dados.update(alteracoes)
    return Servico(**dados)


def test_cria_servico_ativo_e_disponivel_para_os():
    servico = criar_servico()

    assert servico.ativo
    assert servico.pode_ser_incluido_em_os()
    assert servico.id is not None


def test_normaliza_textos():
    servico = criar_servico(codigo=" SRV-001 ", nome=" Troca de óleo ", descricao=" Óleo ")

    assert (servico.codigo, servico.nome, servico.descricao) == ("SRV-001", "Troca de óleo", "Óleo")


@pytest.mark.parametrize("minutos", [0, 1, 480])
def test_aceita_tempo_estimado_nao_negativo(minutos):
    assert criar_servico(tempo_estimado_minutos=minutos).tempo_estimado_minutos == minutos


@pytest.mark.parametrize(
    "alteracao",
    [
        {"codigo": " "},
        {"nome": ""},
        {"descricao": "  "},
        {"valor_base": "120.00"},
        {"tempo_estimado_minutos": -1},
        {"tempo_estimado_minutos": 45.0},
        {"tempo_estimado_minutos": "45"},
        {"tempo_estimado_minutos": True},
    ],
)
def test_rejeita_dados_invalidos(alteracao):
    with pytest.raises(ServicoInvalido) as erro:
        criar_servico(**alteracao)

    assert isinstance(erro.value, ValorInvalido)


def test_altera_valor_base_e_tempo_estimado():
    servico = criar_servico()

    servico.atualizar_dados(
        codigo="SRV-001",
        nome="Troca de óleo",
        descricao="Troca do óleo do motor e do filtro de óleo",
        valor_base=Valor("150.00"),
        tempo_estimado_minutos=60,
    )

    assert servico.valor_base == Valor("150.00")
    assert servico.tempo_estimado_minutos == 60


def test_alteracao_invalida_nao_altera_nenhum_dado():
    servico = criar_servico()

    with pytest.raises(ServicoInvalido):
        servico.atualizar_dados(
            codigo="SRV-002",
            nome="Outro",
            descricao="Outra descrição",
            valor_base=Valor("150.00"),
            tempo_estimado_minutos=-5,
        )

    assert servico.codigo == "SRV-001"
    assert servico.valor_base == Valor("120.00")
    assert servico.tempo_estimado_minutos == 45


def test_servico_excluido_nao_pode_ser_incluido_em_os():
    servico = criar_servico()

    servico.excluir()

    assert not servico.ativo
    assert not servico.pode_ser_incluido_em_os()
    assert servico.nome == "Troca de óleo"


def test_igualdade_pela_identidade():
    servico = criar_servico()

    assert servico != criar_servico()
    assert servico == criar_servico(id=servico.id, nome="Outro nome")
    assert len({servico, criar_servico()}) == 2
