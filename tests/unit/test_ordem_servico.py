from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.exceptions import (
    EntidadeNaoEncontrada,
    ItemIndisponivel,
    ItemJaIncluido,
    ItensBloqueados,
    OrdemServicoInvalida,
    ValorInvalido,
)
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.orcamento import Orcamento
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

STATUS_SEM_EDICAO_DE_ITENS = [s for s in StatusOS if s is not StatusOS.EM_DIAGNOSTICO]


def criar_os(**alteracoes) -> OrdemServico:
    dados = {
        "numero": NumeroOS("529-7F3A9C2B"),
        "cliente_id": uuid4(),
        "veiculo_id": uuid4(),
        "atendente_id": uuid4(),
        "status": StatusOS.EM_DIAGNOSTICO,
    }
    dados.update(alteracoes)
    return OrdemServico(**dados)


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


def criar_peca(**alteracoes) -> Peca:
    dados = {
        "codigo_referencia": "FO-1234",
        "nome": "Filtro de óleo",
        "preco_unitario": Valor("35.90"),
        "prazo_reposicao_dias": 3,
    }
    dados.update(alteracoes)
    return Peca(**dados)


def reajustar_servico(servico: Servico, valor_base: str) -> None:
    servico.atualizar_dados(
        codigo=servico.codigo,
        nome=servico.nome,
        descricao=servico.descricao,
        valor_base=Valor(valor_base),
        tempo_estimado_minutos=servico.tempo_estimado_minutos,
    )


def reajustar_peca(peca: Peca, preco: str) -> None:
    peca.atualizar_dados(
        codigo_referencia=peca.codigo_referencia,
        nome=peca.nome,
        preco_unitario=Valor(preco),
        prazo_reposicao_dias=peca.prazo_reposicao_dias,
    )


def test_abre_a_os_recebida_com_data_de_abertura_e_sem_itens():
    antes = datetime.now(UTC)

    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
    )

    assert os.status is StatusOS.RECEBIDA
    assert os.id is not None
    assert antes <= os.data_abertura <= antes + timedelta(seconds=1)
    assert os.data_abertura.tzinfo is UTC
    assert os.servicos == [] and os.pecas == []
    assert os.orcamento is None


def test_guarda_o_numero_e_as_referencias_a_cliente_veiculo_e_atendente():
    cliente_id, veiculo_id, atendente_id = uuid4(), uuid4(), uuid4()

    os = criar_os(cliente_id=cliente_id, veiculo_id=veiculo_id, atendente_id=atendente_id)

    assert os.numero == NumeroOS("529-7F3A9C2B")
    assert (os.cliente_id, os.veiculo_id, os.atendente_id) == (cliente_id, veiculo_id, atendente_id)


@pytest.mark.parametrize(
    "alteracao",
    [
        {"numero": "529-7F3A9C2B"},
        {"cliente_id": "nao-e-uuid"},
        {"veiculo_id": None},
        {"atendente_id": 123},
    ],
)
def test_recusa_dados_obrigatorios_invalidos(alteracao):
    with pytest.raises(OrdemServicoInvalida) as erro:
        criar_os(**alteracao)

    assert isinstance(erro.value, ValorInvalido)


def test_inclui_servico_e_peca_copiando_os_dados_do_catalogo():
    os = criar_os()
    servico, peca = criar_servico(), criar_peca()

    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=2)

    assert [i.servico_id for i in os.servicos] == [servico.id]
    assert [(i.peca_id, i.quantidade) for i in os.pecas] == [(peca.id, 2)]
    assert os.pecas[0].preco_unitario_congelado == Valor("35.90")


def test_recusa_servico_inativo():
    os = criar_os()
    servico = criar_servico()
    servico.excluir()

    with pytest.raises(ItemIndisponivel):
        os.incluir_servico(servico)

    assert os.servicos == []


def test_recusa_peca_inativa():
    os = criar_os()
    peca = criar_peca()
    peca.excluir()

    with pytest.raises(ItemIndisponivel):
        os.incluir_peca(peca, quantidade=1)

    assert os.pecas == []


def test_recusa_incluir_o_mesmo_servico_ou_a_mesma_peca_duas_vezes():
    os = criar_os()
    servico, peca = criar_servico(), criar_peca()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)

    with pytest.raises(ItemJaIncluido):
        os.incluir_servico(servico)
    with pytest.raises(ItemJaIncluido):
        os.incluir_peca(peca, quantidade=3)

    assert len(os.servicos) == 1
    assert [i.quantidade for i in os.pecas] == [1]


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, "2", True])
def test_recusa_quantidade_de_peca_invalida_sem_incluir_o_item(quantidade):
    os = criar_os()

    with pytest.raises(OrdemServicoInvalida):
        os.incluir_peca(criar_peca(), quantidade=quantidade)

    assert os.pecas == []


def test_remove_servico_e_peca():
    os = criar_os()
    servico, peca = criar_servico(), criar_peca()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)

    os.remover_servico(servico.id)
    os.remover_peca(peca.id)

    assert os.servicos == [] and os.pecas == []


def test_remover_item_que_nao_esta_na_os_levanta_entidade_nao_encontrada():
    os = criar_os()

    with pytest.raises(EntidadeNaoEncontrada):
        os.remover_servico(uuid4())
    with pytest.raises(EntidadeNaoEncontrada):
        os.remover_peca(uuid4())


@pytest.mark.parametrize("status", STATUS_SEM_EDICAO_DE_ITENS)
def test_itens_so_podem_ser_alterados_durante_o_diagnostico(status):
    os = criar_os()
    servico, peca = criar_servico(), criar_peca()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)
    os.status = status

    with pytest.raises(ItensBloqueados) as erro:
        os.incluir_servico(criar_servico(codigo="SRV-002"))
    with pytest.raises(ItensBloqueados):
        os.incluir_peca(criar_peca(codigo_referencia="FO-9999"), quantidade=1)
    with pytest.raises(ItensBloqueados):
        os.remover_servico(servico.id)
    with pytest.raises(ItensBloqueados):
        os.remover_peca(peca.id)
    with pytest.raises(ItensBloqueados):
        os.congelar_valores([servico], [peca])

    assert erro.value.status_atual is status
    assert len(os.servicos) == 1 and len(os.pecas) == 1


def test_orcamento_so_com_servicos():
    os = criar_os()
    os.incluir_servico(criar_servico(valor_base=Valor("120.00")))
    os.incluir_servico(criar_servico(codigo="SRV-002", valor_base=Valor("80.50")))

    os.congelar_valores(_catalogo_de(os)[0], [])

    assert os.orcamento == Orcamento(Valor("200.50"), Valor("0"))
    assert os.orcamento.total == Valor("200.50")


def test_orcamento_so_com_pecas_multiplica_a_quantidade_pelo_preco_unitario():
    os = criar_os()
    os.incluir_peca(criar_peca(preco_unitario=Valor("35.90")), quantidade=3)
    os.incluir_peca(criar_peca(codigo_referencia="PA-1", preco_unitario=Valor("10.00")), 2)

    os.congelar_valores([], _catalogo_de(os)[1])

    assert os.orcamento == Orcamento(Valor("0"), Valor("127.70"))


def test_orcamento_com_servicos_e_pecas():
    servico, peca = criar_servico(valor_base=Valor("120.00")), criar_peca()
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=2)

    os.congelar_valores([servico], [peca])

    assert os.orcamento.subtotal_servicos == Valor("120.00")
    assert os.orcamento.subtotal_pecas == Valor("71.80")
    assert os.orcamento.total == Valor("191.80")


def test_orcamento_de_os_sem_itens_e_zero():
    os = criar_os()

    os.congelar_valores([], [])

    assert os.orcamento.total == Valor("0")


def test_congelar_usa_os_valores_vigentes_do_catalogo_na_conclusao():
    servico, peca = criar_servico(valor_base=Valor("120.00")), criar_peca()
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)
    reajustar_servico(servico, "150.00")
    reajustar_peca(peca, "40.00")

    os.congelar_valores([servico], [peca])

    assert os.orcamento.total == Valor("190.00")
    assert os.servicos[0].preco_congelado == Valor("150.00")
    assert os.pecas[0].preco_unitario_congelado == Valor("40.00")


def test_alterar_o_preco_no_catalogo_depois_da_conclusao_nao_muda_o_orcamento():
    servico, peca = criar_servico(valor_base=Valor("120.00")), criar_peca()
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=2)
    os.congelar_valores([servico], [peca])
    orcamento = os.orcamento

    reajustar_servico(servico, "999.00")
    reajustar_peca(peca, "999.00")

    assert os.orcamento == orcamento
    assert os.orcamento.total == Valor("191.80")
    assert os.servicos[0].preco_congelado == Valor("120.00")
    assert os.pecas[0].preco_unitario_congelado == Valor("35.90")
    assert os.pecas[0].valor_total() == Valor("71.80")


def test_congelar_sem_o_valor_vigente_de_algum_item_nao_altera_nenhum():
    servico, peca = criar_servico(valor_base=Valor("120.00")), criar_peca()
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)
    reajustar_servico(servico, "150.00")

    with pytest.raises(OrdemServicoInvalida, match="Filtro de óleo"):
        os.congelar_valores([servico], [])

    assert os.servicos[0].preco_congelado == Valor("120.00")
    assert os.orcamento is None


def test_igualdade_pela_identidade():
    os = criar_os()

    assert os != criar_os()
    assert os == criar_os(id=os.id)
    assert len({os, criar_os()}) == 2


def _catalogo_de(os: OrdemServico) -> tuple[list[Servico], list[Peca]]:
    """Serviços e peças do catálogo com os mesmos ids e dados dos itens da OS."""
    servicos = [
        Servico(
            codigo=f"S-{i}",
            nome=item.nome,
            descricao="descrição",
            valor_base=item.preco_congelado,
            tempo_estimado_minutos=item.tempo_estimado_minutos,
            id=item.servico_id,
        )
        for i, item in enumerate(os.servicos)
    ]
    pecas = [
        Peca(
            codigo_referencia=f"P-{i}",
            nome=item.nome,
            preco_unitario=item.preco_unitario_congelado,
            prazo_reposicao_dias=item.prazo_reposicao_dias,
            id=item.peca_id,
        )
        for i, item in enumerate(os.pecas)
    ]
    return servicos, pecas
