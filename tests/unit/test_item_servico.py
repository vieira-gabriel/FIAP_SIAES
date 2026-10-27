import pytest

from domain.entities.item_servico import ItemServico
from domain.entities.servico import Servico
from domain.exceptions import OrdemServicoInvalida
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


def reajustar(servico: Servico, valor_base: str, tempo: int) -> None:
    servico.atualizar_dados(
        codigo=servico.codigo,
        nome=servico.nome,
        descricao=servico.descricao,
        valor_base=Valor(valor_base),
        tempo_estimado_minutos=tempo,
    )


def test_copia_nome_preco_e_tempo_do_catalogo():
    servico = criar_servico()

    item = ItemServico.a_partir_de(servico)

    assert item.servico_id == servico.id
    assert item.nome == "Troca de óleo"
    assert item.preco_congelado == Valor("120.00")
    assert item.tempo_estimado_minutos == 45


def test_reajuste_do_catalogo_nao_altera_o_item():
    servico = criar_servico()
    item = ItemServico.a_partir_de(servico)

    reajustar(servico, "150.00", 60)

    assert item.preco_congelado == Valor("120.00")
    assert item.tempo_estimado_minutos == 45


def test_congelar_atualiza_com_os_valores_vigentes_do_catalogo():
    servico = criar_servico()
    item = ItemServico.a_partir_de(servico)
    reajustar(servico, "150.00", 60)

    item.congelar(servico)

    assert item.preco_congelado == Valor("150.00")
    assert item.tempo_estimado_minutos == 60


def test_congelar_recusa_servico_diferente_do_item():
    item = ItemServico.a_partir_de(criar_servico())

    with pytest.raises(OrdemServicoInvalida):
        item.congelar(criar_servico())


def test_igualdade_pelo_servico_do_catalogo():
    servico = criar_servico()

    assert ItemServico.a_partir_de(servico) == ItemServico.a_partir_de(servico)
    assert ItemServico.a_partir_de(servico) != ItemServico.a_partir_de(criar_servico())
    assert len({ItemServico.a_partir_de(servico), ItemServico.a_partir_de(servico)}) == 1
