from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.estoque_peca import EstoquePeca
from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.entities.usuario import Usuario
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.exceptions import (
    AcessoNegado,
    EntidadeNaoEncontrada,
    ItemIndisponivel,
    ItemJaIncluido,
    ItensBloqueados,
    MecanicoIndisponivel,
    MotivoInvalido,
    MotivoObrigatorio,
    OrdemServicoInvalida,
    PecasPendentes,
    TransicaoDeStatusInvalida,
    ValorInvalido,
)
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.orcamento import Orcamento
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.pendencia_peca import PendenciaPeca
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.quantidade_peca import QuantidadePeca
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

STATUS_SEM_EDICAO_DE_ITENS = [s for s in StatusOS if s is not StatusOS.EM_DIAGNOSTICO]
USUARIO_ID = uuid4()


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
    peca.excluir([])

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


@pytest.mark.parametrize("excluido", ["servico", "peca"])
def test_congelar_com_item_excluido_do_catalogo_nao_altera_nenhum(excluido):
    servico, peca = criar_servico(valor_base=Valor("120.00")), criar_peca()
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)
    reajustar_servico(servico, "150.00")
    if excluido == "servico":
        servico.excluir()
    else:
        peca.excluir([])

    with pytest.raises(ItemIndisponivel):
        os.congelar_valores([servico], [peca])

    assert os.servicos[0].preco_congelado == Valor("120.00")
    assert os.orcamento is None


def test_congelar_ignora_item_excluido_que_nao_esta_na_os():
    servico, sem_uso = criar_servico(), criar_servico(codigo="SRV-002")
    sem_uso.excluir()
    os = criar_os()
    os.incluir_servico(servico)

    os.congelar_valores([servico, sem_uso], [])

    assert os.orcamento.total == Valor("120.00")


@pytest.mark.parametrize(
    "alteracao",
    [
        {"data_abertura": datetime(2026, 10, 27, 12, 0)},
        {"data_abertura": "ontem"},
        {"data_abertura": None},
        {"status": "QUALQUER"},
        {"status": None},
        {"status": 3},
    ],
    ids=[
        "data sem fuso",
        "data texto",
        "data nula",
        "status texto",
        "status nulo",
        "status numero",
    ],
)
def test_recusa_data_de_abertura_sem_fuso_e_status_fora_do_status_os(alteracao):
    with pytest.raises(OrdemServicoInvalida):
        criar_os(**alteracao)


def test_incluir_ou_remover_item_descarta_o_orcamento_ja_calculado():
    primeiro, segundo, peca = criar_servico(), criar_servico(codigo="SRV-002"), criar_peca()
    os = criar_os()
    os.incluir_servico(primeiro)
    os.congelar_valores([primeiro], [])
    assert os.orcamento is not None

    os.incluir_servico(segundo)
    assert os.orcamento is None

    os.congelar_valores([primeiro, segundo], [])
    os.incluir_peca(peca, quantidade=1)
    assert os.orcamento is None

    os.congelar_valores([primeiro, segundo], [peca])
    os.remover_peca(peca.id)
    assert os.orcamento is None

    os.congelar_valores([primeiro, segundo], [])
    os.remover_servico(segundo.id)
    assert os.orcamento is None


def test_recongelar_depois_de_mudar_os_itens_calcula_o_orcamento_com_todos_eles():
    primeiro, segundo = criar_servico(valor_base=Valor("100.00")), criar_servico(codigo="SRV-002")
    reajustar_servico(segundo, "500.00")
    os = criar_os()
    os.incluir_servico(primeiro)
    os.congelar_valores([primeiro], [])

    os.incluir_servico(segundo)
    os.congelar_valores([primeiro, segundo], [])

    assert os.orcamento.total == Valor("600.00")


def test_item_recusado_nao_descarta_o_orcamento():
    servico = criar_servico()
    os = criar_os()
    os.incluir_servico(servico)
    os.congelar_valores([servico], [])

    with pytest.raises(ItemJaIncluido):
        os.incluir_servico(servico)
    with pytest.raises(EntidadeNaoEncontrada):
        os.remover_peca(uuid4())

    assert os.orcamento is not None


def test_igualdade_pela_identidade():
    os = criar_os()

    assert os != criar_os()
    assert os == criar_os(id=os.id)
    assert len({os, criar_os()}) == 2


def fora_de(*permitidos: StatusOS) -> list[StatusOS]:
    return [status for status in StatusOS if status not in permitidos]


def _recusada_sem_alterar(os: OrdemServico) -> None:
    assert os.status is StatusOS.RECEBIDA
    assert os.mecanico_id is None
    assert os.historico == ()


def test_mecanico_atribui_a_os_a_si_mesmo_e_ela_vai_para_em_diagnostico():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=StatusOS.RECEBIDA)

    os.atribuir_mecanico(mecanico, mecanico)

    assert os.status is StatusOS.EM_DIAGNOSTICO
    assert os.mecanico_id == mecanico.id
    registro = os.historico[-1]
    assert (registro.status_anterior, registro.status_novo) == (
        StatusOS.RECEBIDA,
        StatusOS.EM_DIAGNOSTICO,
    )
    assert registro.origem is OrigemTransicao.USUARIO
    assert registro.usuario_id == mecanico.id


def test_gerente_atribui_a_os_a_um_mecanico_e_o_historico_grava_o_gerente():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    gerente = criar_usuario(PerfilUsuario.GERENTE)
    os = criar_os(status=StatusOS.RECEBIDA)

    os.atribuir_mecanico(mecanico, gerente)

    assert os.status is StatusOS.EM_DIAGNOSTICO
    assert os.mecanico_id == mecanico.id
    assert os.historico[-1].usuario_id == gerente.id


@pytest.mark.parametrize("status", fora_de(StatusOS.RECEBIDA))
def test_atribuir_mecanico_so_a_partir_de_recebida(status):
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.atribuir_mecanico(mecanico, mecanico)

    assert erro.value.status_atual is status
    assert erro.value.status_pretendido is StatusOS.EM_DIAGNOSTICO
    assert os.status is status
    assert os.mecanico_id is None


def test_mecanico_nao_atribui_a_os_a_outro_mecanico():
    os = criar_os(status=StatusOS.RECEBIDA)

    with pytest.raises(AcessoNegado):
        os.atribuir_mecanico(
            criar_usuario(PerfilUsuario.MECANICO), criar_usuario(PerfilUsuario.MECANICO)
        )

    _recusada_sem_alterar(os)


def test_atendente_nao_atribui_mecanico():
    os = criar_os(status=StatusOS.RECEBIDA)

    with pytest.raises(AcessoNegado):
        os.atribuir_mecanico(
            criar_usuario(PerfilUsuario.MECANICO), criar_usuario(PerfilUsuario.ATENDENTE)
        )

    _recusada_sem_alterar(os)


@pytest.mark.parametrize("perfil", [PerfilUsuario.GERENTE, PerfilUsuario.MECANICO])
def test_responsavel_desativado_nao_atribui_mecanico(perfil):
    responsavel = criar_usuario(perfil, ativo=False)
    mecanico = responsavel if perfil is PerfilUsuario.MECANICO else criar_usuario(perfil)
    os = criar_os(status=StatusOS.RECEBIDA)

    with pytest.raises(AcessoNegado, match="desativado"):
        os.atribuir_mecanico(mecanico, responsavel)

    _recusada_sem_alterar(os)


@pytest.mark.parametrize(
    ("perfil", "ativo"),
    [
        (PerfilUsuario.GERENTE, True),
        (PerfilUsuario.ATENDENTE, True),
        (PerfilUsuario.MECANICO, False),
    ],
)
def test_gerente_so_atribui_a_os_a_mecanico_ativo(perfil, ativo):
    os = criar_os(status=StatusOS.RECEBIDA)

    with pytest.raises(MecanicoIndisponivel):
        os.atribuir_mecanico(criar_usuario(perfil, ativo), criar_usuario(PerfilUsuario.GERENTE))

    _recusada_sem_alterar(os)


@pytest.mark.parametrize("invalido", ["nao-e-usuario", None, 123, uuid4()])
def test_atribuir_mecanico_recusa_mecanico_ou_responsavel_invalido(invalido):
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=StatusOS.RECEBIDA)

    with pytest.raises(OrdemServicoInvalida):
        os.atribuir_mecanico(invalido, mecanico)
    with pytest.raises(OrdemServicoInvalida):
        os.atribuir_mecanico(mecanico, invalido)

    _recusada_sem_alterar(os)


def test_finalizar_orcamento_congela_os_valores_vigentes_e_aguarda_a_aprovacao():
    servico, peca = criar_servico(valor_base=Valor("120.00")), criar_peca()
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=2)
    reajustar_servico(servico, "150.00")

    os.finalizar_orcamento(USUARIO_ID, [servico], [peca])

    assert os.status is StatusOS.AGUARDANDO_APROVACAO
    assert os.orcamento.total == Valor("221.80")


@pytest.mark.parametrize("status", fora_de(StatusOS.EM_DIAGNOSTICO))
def test_finalizar_orcamento_so_a_partir_de_em_diagnostico(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.finalizar_orcamento(USUARIO_ID, [], [])

    assert erro.value.status_pretendido is StatusOS.AGUARDANDO_APROVACAO
    assert os.status is status
    assert os.orcamento is None


def test_finalizar_orcamento_sem_valor_vigente_mantem_o_diagnostico():
    os = criar_os()
    os.incluir_peca(criar_peca(), quantidade=1)

    with pytest.raises(OrdemServicoInvalida):
        os.finalizar_orcamento(USUARIO_ID, [], [])

    assert os.status is StatusOS.EM_DIAGNOSTICO
    assert os.orcamento is None


def test_finalizar_orcamento_com_peca_excluida_mantem_o_diagnostico_sem_pendencia():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=1)
    peca.excluir([])

    with pytest.raises(ItemIndisponivel):
        os.finalizar_orcamento(USUARIO_ID, [], [peca])

    assert os.status is StatusOS.EM_DIAGNOSTICO
    assert os.pecas[0].quantidade_pendente == 0


def criar_usuario(perfil: PerfilUsuario, ativo: bool = True) -> Usuario:
    return Usuario(
        nome="Ana", email="ana@oficina.com", senha_hash="hash", perfil=perfil, ativo=ativo
    )


def os_aguardando_aprovacao_com_peca_pendente() -> OrdemServico:
    """Duas unidades da peça: uma reservada e uma pendente."""
    peca = criar_peca()
    os = criar_os(status=StatusOS.EM_DIAGNOSTICO)
    os.incluir_peca(peca, quantidade=2)
    os.finalizar_orcamento(USUARIO_ID, [], [peca])
    os.pecas[0].quantidade_reservada = 1
    os.pecas[0].quantidade_pendente = 1
    return os


def test_aprovar_orcamento_sem_pecas_pendentes_aguarda_a_execucao():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=2)
    os.finalizar_orcamento(USUARIO_ID, [], [peca])
    os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente = 2, 0

    os.aprovar_orcamento()

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO


def test_finalizar_orcamento_deixa_toda_a_quantidade_das_pecas_pendente_de_reserva():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=3)

    os.finalizar_orcamento(USUARIO_ID, [], [peca])

    assert (os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente) == (0, 3)


def test_aprovar_antes_da_reserva_de_estoque_aguarda_a_peca():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=1)
    os.finalizar_orcamento(USUARIO_ID, [], [peca])

    os.aprovar_orcamento()

    assert os.status is StatusOS.AGUARDANDO_PECA


def test_aprovar_orcamento_com_pecas_pendentes_aguarda_a_peca():
    os = os_aguardando_aprovacao_com_peca_pendente()

    os.aprovar_orcamento()

    assert os.status is StatusOS.AGUARDANDO_PECA


@pytest.mark.parametrize("status", fora_de(StatusOS.AGUARDANDO_APROVACAO))
def test_aprovar_orcamento_so_a_partir_de_aguardando_aprovacao(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida):
        os.aprovar_orcamento()

    assert os.status is status


def test_rejeitar_orcamento_cancela_a_os():
    os = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)

    os.rejeitar_orcamento()

    assert os.status is StatusOS.CANCELADA


def test_rejeitar_orcamento_descarta_as_pendencias_e_mantem_as_reservadas():
    os = os_aguardando_aprovacao_com_peca_pendente()

    os.rejeitar_orcamento()

    assert os.status is StatusOS.CANCELADA
    assert (os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente) == (1, 0)


def test_cancelar_descarta_as_pendencias_e_mantem_as_reservadas():
    os = os_aguardando_aprovacao_com_peca_pendente()
    os.aprovar_orcamento()
    assert os.status is StatusOS.AGUARDANDO_PECA

    os.cancelar(USUARIO_ID, "Cliente desistiu do serviço")

    assert os.status is StatusOS.CANCELADA
    assert (os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente) == (1, 0)


def test_cancelar_os_sem_pendencias_nao_altera_os_itens():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=2)
    os.finalizar_orcamento(USUARIO_ID, [], [peca])
    os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente = 2, 0

    os.cancelar(USUARIO_ID, "Cliente desistiu do serviço")

    assert (os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente) == (2, 0)


def test_transicao_ou_motivo_recusados_nao_descartam_as_pendencias():
    os = os_aguardando_aprovacao_com_peca_pendente()
    os.aprovar_orcamento()

    with pytest.raises(TransicaoDeStatusInvalida):
        os.rejeitar_orcamento()
    with pytest.raises(MotivoObrigatorio):
        os.cancelar(USUARIO_ID, "  ")

    assert os.status is StatusOS.AGUARDANDO_PECA
    assert os.pecas[0].quantidade_pendente == 1


def test_decisao_do_cliente_grava_a_origem_cliente_sem_usuario():
    aprovada = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)
    rejeitada = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)

    aprovada.aprovar_orcamento()
    rejeitada.rejeitar_orcamento()

    for os in (aprovada, rejeitada):
        assert (os.historico[-1].origem, os.historico[-1].usuario_id) == (
            OrigemTransicao.CLIENTE,
            None,
        )


def test_decisao_registrada_no_balcao_grava_o_funcionario():
    aprovada = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)
    rejeitada = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)

    aprovada.aprovar_orcamento(USUARIO_ID)
    rejeitada.rejeitar_orcamento(USUARIO_ID)

    assert aprovada.status is StatusOS.AGUARDANDO_EXECUCAO
    assert rejeitada.status is StatusOS.CANCELADA
    for os in (aprovada, rejeitada):
        assert (os.historico[-1].origem, os.historico[-1].usuario_id) == (
            OrigemTransicao.USUARIO,
            USUARIO_ID,
        )


def test_rejeicao_no_balcao_emite_o_cancelamento_para_o_estorno():
    os = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)

    os.rejeitar_orcamento(USUARIO_ID)

    assert [type(evento) for evento in os.collect_domain_events()] == [OSCanceladaEvent]


@pytest.mark.parametrize("decidir", ["aprovar_orcamento", "rejeitar_orcamento"])
def test_decisao_no_balcao_recusa_usuario_que_nao_e_uuid(decidir):
    os = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)

    with pytest.raises(OrdemServicoInvalida):
        getattr(os, decidir)("atendente")

    assert os.status is StatusOS.AGUARDANDO_APROVACAO


@pytest.mark.parametrize("status", fora_de(StatusOS.AGUARDANDO_APROVACAO))
def test_rejeitar_orcamento_so_a_partir_de_aguardando_aprovacao(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.rejeitar_orcamento()

    assert erro.value.status_pretendido is StatusOS.CANCELADA
    assert os.status is status


def test_liberar_para_execucao_sem_pecas_pendentes():
    os = os_aguardando_aprovacao_com_peca_pendente()
    os.aprovar_orcamento()
    os.pecas[0].quantidade_reservada = 2
    os.pecas[0].quantidade_pendente = 0

    os.liberar_para_execucao()

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO


def test_liberar_para_execucao_com_peca_pendente_e_recusado():
    os = os_aguardando_aprovacao_com_peca_pendente()
    os.aprovar_orcamento()

    with pytest.raises(PecasPendentes) as erro:
        os.liberar_para_execucao()

    assert erro.value.pecas == ["Filtro de óleo"]
    assert os.status is StatusOS.AGUARDANDO_PECA


@pytest.mark.parametrize("status", fora_de(StatusOS.AGUARDANDO_PECA))
def test_liberar_para_execucao_so_a_partir_de_aguardando_peca(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.liberar_para_execucao()

    assert erro.value.status_pretendido is StatusOS.AGUARDANDO_EXECUCAO
    assert os.status is status


def test_mecanico_atribuido_inicia_a_execucao_e_grava_o_momento_do_inicio():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=mecanico.id)
    antes = datetime.now(UTC)

    os.iniciar_execucao(mecanico)

    assert os.status is StatusOS.EM_EXECUCAO
    assert os.data_inicio_execucao.tzinfo is UTC
    assert antes <= os.data_inicio_execucao <= antes + timedelta(seconds=1)


def test_gerente_inicia_a_execucao_de_os_de_outro_mecanico():
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=uuid4())

    os.iniciar_execucao(criar_usuario(PerfilUsuario.GERENTE))

    assert os.status is StatusOS.EM_EXECUCAO


@pytest.mark.parametrize("perfil", [PerfilUsuario.MECANICO, PerfilUsuario.ATENDENTE])
def test_outro_usuario_nao_inicia_a_execucao(perfil):
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=uuid4())

    with pytest.raises(AcessoNegado):
        os.iniciar_execucao(criar_usuario(perfil))

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO
    assert os.data_inicio_execucao is None


@pytest.mark.parametrize("perfil", [PerfilUsuario.GERENTE, PerfilUsuario.MECANICO])
def test_usuario_desativado_nao_inicia_a_execucao_mesmo_sendo_gerente_ou_o_atribuido(perfil):
    usuario = criar_usuario(perfil, ativo=False)
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=usuario.id)

    with pytest.raises(AcessoNegado, match="desativado"):
        os.iniciar_execucao(usuario)

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO
    assert os.data_inicio_execucao is None


@pytest.mark.parametrize("usuario", [None, "nao-e-usuario", uuid4()])
def test_iniciar_execucao_recusa_usuario_invalido(usuario):
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO)

    with pytest.raises(OrdemServicoInvalida):
        os.iniciar_execucao(usuario)

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO


@pytest.mark.parametrize("status", fora_de(StatusOS.AGUARDANDO_EXECUCAO))
def test_iniciar_execucao_so_a_partir_de_aguardando_execucao(status):
    gerente = criar_usuario(PerfilUsuario.GERENTE)
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.iniciar_execucao(gerente)

    assert erro.value.status_pretendido is StatusOS.EM_EXECUCAO
    assert os.status is status
    assert os.data_inicio_execucao is None


@pytest.mark.parametrize(
    "status", fora_de(StatusOS.FINALIZADA, StatusOS.ENTREGUE, StatusOS.CANCELADA)
)
def test_cancelar_de_recebida_ate_em_execucao(status):
    os = criar_os(status=status)

    os.cancelar(USUARIO_ID, "Cliente desistiu do serviço")

    assert os.status is StatusOS.CANCELADA


@pytest.mark.parametrize("status", [StatusOS.FINALIZADA, StatusOS.ENTREGUE, StatusOS.CANCELADA])
def test_nao_cancela_os_finalizada_entregue_ou_cancelada(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.cancelar(USUARIO_ID, "Qualquer motivo")

    assert erro.value.status_pretendido is StatusOS.CANCELADA
    assert os.status is status


@pytest.mark.parametrize("motivo", ["<b>desistiu</b>", "valor < 10", "<"])
def test_cancelar_recusa_o_motivo_com_marcacao(motivo):
    os = criar_os(status=StatusOS.AGUARDANDO_PECA)

    with pytest.raises(MotivoInvalido):
        os.cancelar(USUARIO_ID, motivo)

    assert (os.status, os.historico) == (StatusOS.AGUARDANDO_PECA, ())


def test_cancelar_aceita_o_motivo_com_acentos_e_outros_simbolos():
    os = criar_os(status=StatusOS.AGUARDANDO_PECA)

    os.cancelar(USUARIO_ID, "Cliente desistiu & levou o carro > 10 dias")

    assert os.status is StatusOS.CANCELADA


@pytest.mark.parametrize("motivo", ["", "   ", None])
def test_cancelar_exige_o_motivo(motivo):
    os = criar_os(status=StatusOS.AGUARDANDO_PECA)

    with pytest.raises(MotivoObrigatorio):
        os.cancelar(USUARIO_ID, motivo)

    assert os.status is StatusOS.AGUARDANDO_PECA


def test_fluxo_completo_sem_pecas_pendentes():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    servico = criar_servico()
    os = criar_os(status=StatusOS.RECEBIDA)

    os.atribuir_mecanico(mecanico, mecanico)
    os.incluir_servico(servico)
    os.finalizar_orcamento(USUARIO_ID, [servico], [])
    os.aprovar_orcamento()
    os.iniciar_execucao(mecanico)
    os.concluir_manutencao(mecanico)
    os.entregar_veiculo(USUARIO_ID)

    assert os.status is StatusOS.ENTREGUE
    assert os.orcamento.total == Valor("120.00")
    assert os.data_abertura <= os.data_inicio_execucao <= os.data_finalizacao


def test_fluxo_completo_com_espera_pela_peca():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = os_aguardando_aprovacao_com_peca_pendente()
    os.mecanico_id = mecanico.id

    os.aprovar_orcamento()
    assert os.status is StatusOS.AGUARDANDO_PECA
    os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente = 2, 0
    os.liberar_para_execucao()
    os.iniciar_execucao(mecanico)

    assert os.status is StatusOS.EM_EXECUCAO


def test_concluir_manutencao_grava_o_momento_da_conclusao():
    os = criar_os(status=StatusOS.EM_EXECUCAO)
    antes = datetime.now(UTC)

    os.concluir_manutencao(criar_usuario(PerfilUsuario.GERENTE))

    assert os.status is StatusOS.FINALIZADA
    assert os.data_finalizacao.tzinfo is UTC
    assert antes <= os.data_finalizacao <= antes + timedelta(seconds=1)


def test_concluir_manutencao_pelo_mecanico_atribuido_registra_o_usuario():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=StatusOS.EM_EXECUCAO, mecanico_id=mecanico.id)

    os.concluir_manutencao(mecanico)

    assert os.status is StatusOS.FINALIZADA
    assert os.historico[-1].usuario_id == mecanico.id


def test_concluir_manutencao_recusa_o_mecanico_que_nao_e_o_atribuido():
    atribuido = criar_usuario(PerfilUsuario.MECANICO)
    outro = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=StatusOS.EM_EXECUCAO, mecanico_id=atribuido.id)

    with pytest.raises(AcessoNegado):
        os.concluir_manutencao(outro)

    assert os.status is StatusOS.EM_EXECUCAO
    assert os.data_finalizacao is None


@pytest.mark.parametrize("perfil", [PerfilUsuario.MECANICO, PerfilUsuario.GERENTE])
def test_concluir_manutencao_recusa_o_usuario_desativado(perfil):
    usuario = criar_usuario(perfil, ativo=False)
    os = criar_os(status=StatusOS.EM_EXECUCAO, mecanico_id=usuario.id)

    with pytest.raises(AcessoNegado):
        os.concluir_manutencao(usuario)

    assert os.status is StatusOS.EM_EXECUCAO


def test_concluir_manutencao_exige_o_usuario():
    os = criar_os(status=StatusOS.EM_EXECUCAO)

    with pytest.raises(OrdemServicoInvalida):
        os.concluir_manutencao(None)

    assert os.status is StatusOS.EM_EXECUCAO


@pytest.mark.parametrize("status", fora_de(StatusOS.EM_EXECUCAO))
def test_concluir_manutencao_so_a_partir_de_em_execucao(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.concluir_manutencao(criar_usuario(PerfilUsuario.GERENTE))

    assert erro.value.status_pretendido is StatusOS.FINALIZADA
    assert os.status is status
    assert os.data_finalizacao is None


def test_itens_ficam_bloqueados_depois_de_finalizada():
    os = criar_os(status=StatusOS.EM_EXECUCAO)
    os.concluir_manutencao(criar_usuario(PerfilUsuario.GERENTE))

    with pytest.raises(ItensBloqueados) as erro:
        os.incluir_servico(criar_servico())

    assert erro.value.status_atual is StatusOS.FINALIZADA


def test_entregar_veiculo_leva_a_os_finalizada_para_entregue():
    os = criar_os(status=StatusOS.FINALIZADA)

    os.entregar_veiculo(USUARIO_ID)

    assert os.status is StatusOS.ENTREGUE


@pytest.mark.parametrize("status", fora_de(StatusOS.FINALIZADA))
def test_entregar_veiculo_so_a_partir_de_finalizada(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.entregar_veiculo(USUARIO_ID)

    assert erro.value.status_pretendido is StatusOS.ENTREGUE
    assert os.status is status


def test_a_os_abre_sem_mecanico_e_sem_timestamps_de_execucao():
    os = criar_os(status=StatusOS.RECEBIDA)

    assert os.mecanico_id is None
    assert os.data_inicio_execucao is None
    assert os.data_finalizacao is None


def sequencia(os: OrdemServico) -> list[tuple]:
    return [(r.status_anterior, r.status_novo, r.origem, r.usuario_id) for r in os.historico]


def abrir_os(**alteracoes) -> OrdemServico:
    dados = {
        "numero": NumeroOS("529-7F3A9C2B"),
        "cliente_id": uuid4(),
        "veiculo_id": uuid4(),
        "atendente_id": uuid4(),
    }
    dados.update(alteracoes)
    return OrdemServico.abrir(**dados)


def reconstituir(os: OrdemServico, **alteracoes) -> OrdemServico:
    """A mesma OS lida do banco: os dados e o `id`, com o histórico só se a leitura o trouxer."""
    dados = {
        "id": os.id,
        "numero": os.numero,
        "cliente_id": os.cliente_id,
        "veiculo_id": os.veiculo_id,
        "atendente_id": os.atendente_id,
        "data_abertura": os.data_abertura,
        "status": os.status,
    }
    dados.update(alteracoes)
    return OrdemServico(**dados)


def test_abrir_gera_o_primeiro_registro_do_historico_sem_status_anterior():
    atendente_id = uuid4()

    os = abrir_os(atendente_id=atendente_id)

    assert os.status is StatusOS.RECEBIDA
    assert len(os.historico) == 1
    registro = os.historico[0]
    assert registro.status_anterior is None
    assert registro.status_novo is StatusOS.RECEBIDA
    assert registro.origem is OrigemTransicao.USUARIO
    assert registro.usuario_id == atendente_id
    assert registro.data_hora == os.data_abertura


def test_abrir_usa_o_id_informado_ou_gera_um():
    os_id = uuid4()

    assert abrir_os(id=os_id).id == os_id
    assert abrir_os().id is not None
    assert abrir_os().id != abrir_os().id


@pytest.mark.parametrize(
    "alteracao",
    [{"numero": "529-7F3A9C2B"}, {"cliente_id": "x"}, {"id": "nao-e-uuid"}],
)
def test_abrir_recusa_dados_invalidos(alteracao):
    with pytest.raises(OrdemServicoInvalida):
        abrir_os(**alteracao)


def test_o_construtor_nunca_inventa_o_registro_de_abertura():
    assert criar_os(status=StatusOS.RECEBIDA).historico == ()
    assert criar_os(status=StatusOS.EM_EXECUCAO).historico == ()


def test_ler_a_mesma_os_duas_vezes_nao_duplica_nem_cria_registros():
    aberta = abrir_os()

    com_historico = reconstituir(aberta, historico=aberta.historico)
    sem_historico = [reconstituir(aberta), reconstituir(aberta)]

    assert com_historico.historico == aberta.historico
    assert com_historico.historico[0] is aberta.historico[0]
    assert [os.historico for os in sem_historico] == [(), ()]


def test_historico_reconstituido_aceita_lista_e_vira_tupla():
    aberta = abrir_os()

    os = reconstituir(aberta, historico=list(aberta.historico))

    assert isinstance(os.historico, tuple)
    assert os.historico == aberta.historico


def _registro(anterior, novo, dias=0, origem=OrigemTransicao.USUARIO):
    return HistoricoStatusOS(
        status_anterior=anterior,
        status_novo=novo,
        data_hora=datetime(2026, 10, 1, tzinfo=UTC) + timedelta(days=dias),
        origem=origem,
        usuario_id=uuid4() if origem is OrigemTransicao.USUARIO else None,
    )


def test_historico_reconstituido_encadeado_e_terminando_no_status_e_aceito():
    historico = [
        _registro(None, StatusOS.RECEBIDA, 0),
        _registro(StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO, 1),
    ]

    os = criar_os(status=StatusOS.EM_DIAGNOSTICO, historico=historico)

    assert [r.status_novo for r in os.historico] == [StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO]


def _historicos_incoerentes() -> dict:
    abertura = _registro(None, StatusOS.RECEBIDA, 0)
    diagnostico = _registro(StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO, 1)
    salto = _registro(StatusOS.EM_DIAGNOSTICO, StatusOS.EM_EXECUCAO, 2)
    return {
        "so a abertura, mas a OS esta cancelada": (StatusOS.CANCELADA, [abertura]),
        "registros fora de ordem": (StatusOS.EM_DIAGNOSTICO, [diagnostico, abertura]),
        "registro que nao encadeia": (StatusOS.EM_EXECUCAO, [abertura, salto]),
        "item que nao e registro": (StatusOS.RECEBIDA, ["lixo"]),
        "historico nulo": (StatusOS.RECEBIDA, None),
        "historico de outro tipo": (StatusOS.RECEBIDA, "abertura"),
    }


@pytest.mark.parametrize("caso", list(_historicos_incoerentes()))
def test_recusa_historico_incoerente_na_reconstituicao(caso):
    status, registros = _historicos_incoerentes()[caso]

    with pytest.raises(OrdemServicoInvalida):
        criar_os(status=status, historico=registros)


def test_o_historico_da_os_e_somente_leitura():
    os = abrir_os()
    registro = os.historico[0]

    with pytest.raises(AttributeError):
        os.historico.append(registro)
    with pytest.raises(AttributeError):
        os.historico.clear()
    with pytest.raises(TypeError):
        os.historico[0] = registro
    with pytest.raises(TypeError):
        del os.historico[0]
    with pytest.raises(AttributeError):
        os.historico = ()

    assert os.historico == (registro,)


def test_o_historico_so_cresce_pelas_transicoes():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = abrir_os()
    antes = os.historico

    os.atribuir_mecanico(mecanico, mecanico)

    assert os.historico[:1] == antes
    assert len(os.historico) == 2
    assert antes == os.historico[:1]


def test_recusa_data_de_abertura_que_nao_e_data():
    with pytest.raises(OrdemServicoInvalida):
        criar_os(data_abertura="ontem")


def test_fluxo_completo_registra_a_sequencia_de_transicoes():
    atendente_id = uuid4()
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    servico = criar_servico()
    os = abrir_os(atendente_id=atendente_id)

    os.atribuir_mecanico(mecanico, mecanico)
    os.incluir_servico(servico)
    os.finalizar_orcamento(mecanico.id, [servico], [])
    os.aprovar_orcamento()
    os.iniciar_execucao(mecanico)
    os.concluir_manutencao(mecanico)
    os.entregar_veiculo(atendente_id)

    usuario, cliente = OrigemTransicao.USUARIO, OrigemTransicao.CLIENTE
    assert sequencia(os) == [
        (None, StatusOS.RECEBIDA, usuario, atendente_id),
        (StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO, usuario, mecanico.id),
        (StatusOS.EM_DIAGNOSTICO, StatusOS.AGUARDANDO_APROVACAO, usuario, mecanico.id),
        (StatusOS.AGUARDANDO_APROVACAO, StatusOS.AGUARDANDO_EXECUCAO, cliente, None),
        (StatusOS.AGUARDANDO_EXECUCAO, StatusOS.EM_EXECUCAO, usuario, mecanico.id),
        (StatusOS.EM_EXECUCAO, StatusOS.FINALIZADA, usuario, mecanico.id),
        (StatusOS.FINALIZADA, StatusOS.ENTREGUE, usuario, atendente_id),
    ]
    datas = [registro.data_hora for registro in os.historico]
    assert datas == sorted(datas)


def test_fluxo_com_espera_de_peca_registra_a_liberacao_pelo_sistema():
    os = os_aguardando_aprovacao_com_peca_pendente()
    os.aprovar_orcamento()
    os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente = 2, 0

    os.liberar_para_execucao()

    assert sequencia(os)[-2:] == [
        (StatusOS.AGUARDANDO_APROVACAO, StatusOS.AGUARDANDO_PECA, OrigemTransicao.CLIENTE, None),
        (StatusOS.AGUARDANDO_PECA, StatusOS.AGUARDANDO_EXECUCAO, OrigemTransicao.SISTEMA, None),
    ]


def test_rejeitar_orcamento_registra_a_origem_cliente_sem_usuario_nem_motivo():
    os = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)

    os.rejeitar_orcamento()

    registro = os.historico[-1]
    assert registro.status_novo is StatusOS.CANCELADA
    assert registro.origem is OrigemTransicao.CLIENTE
    assert registro.usuario_id is None
    assert registro.motivo is None


def test_cancelar_registra_o_usuario_e_o_motivo_no_historico():
    gerente_id = uuid4()
    os = criar_os(status=StatusOS.EM_EXECUCAO)

    os.cancelar(gerente_id, "  Cliente desistiu do serviço ")

    registro = os.historico[-1]
    assert (registro.status_anterior, registro.status_novo) == (
        StatusOS.EM_EXECUCAO,
        StatusOS.CANCELADA,
    )
    assert registro.origem is OrigemTransicao.USUARIO
    assert registro.usuario_id == gerente_id
    assert registro.motivo == "Cliente desistiu do serviço"


def test_o_registro_usa_o_mesmo_instante_dos_timestamps_da_os():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=mecanico.id)

    os.iniciar_execucao(mecanico)
    assert os.historico[-1].data_hora == os.data_inicio_execucao

    os.concluir_manutencao(mecanico)
    assert os.historico[-1].data_hora == os.data_finalizacao


def test_transicao_recusada_nao_gera_registro():
    os = abrir_os()

    with pytest.raises(TransicaoDeStatusInvalida):
        os.concluir_manutencao(criar_usuario(PerfilUsuario.GERENTE))
    with pytest.raises(MotivoObrigatorio):
        os.cancelar(USUARIO_ID, "")

    assert len(os.historico) == 1
    assert os.status is StatusOS.RECEBIDA


@pytest.mark.parametrize("usuario_id", ["nao-e-uuid", None])
def test_transicoes_feitas_por_usuario_exigem_o_usuario(usuario_id):
    os = criar_os()

    with pytest.raises(OrdemServicoInvalida):
        os.finalizar_orcamento(usuario_id, [], [])
    with pytest.raises(OrdemServicoInvalida):
        os.cancelar(usuario_id, "Motivo")
    with pytest.raises(OrdemServicoInvalida):
        os.concluir_manutencao(usuario_id)
    with pytest.raises(OrdemServicoInvalida):
        os.entregar_veiculo(usuario_id)

    assert os.status is StatusOS.EM_DIAGNOSTICO
    assert os.historico == ()


def test_finalizar_orcamento_com_usuario_invalido_nao_congela_os_itens():
    servico = criar_servico(valor_base=Valor("120.00"))
    os = criar_os()
    os.incluir_servico(servico)
    reajustar_servico(servico, "150.00")

    with pytest.raises(OrdemServicoInvalida):
        os.finalizar_orcamento(None, [servico], [])

    assert os.servicos[0].preco_congelado == Valor("120.00")
    assert os.orcamento is None


def test_registro_do_historico_nao_pode_ser_alterado_pela_os():
    os = abrir_os()

    with pytest.raises(FrozenInstanceError):
        os.historico[0].status_novo = StatusOS.CANCELADA

    assert os.historico[0].status_novo is StatusOS.RECEBIDA


MOMENTO_DA_CONSULTA = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def os_com_itens(status: StatusOS, *, minutos=(), pecas=(), **alteracoes) -> OrdemServico:
    """OS no status pedido, com serviços de `minutos` e peças de (prazo, quantidade pendente).

    Cada peça tem 2 unidades; o que não está pendente já está reservado.
    """
    os = criar_os(status=StatusOS.EM_DIAGNOSTICO)
    for numero, tempo in enumerate(minutos):
        os.incluir_servico(criar_servico(codigo=f"SRV-{numero}", tempo_estimado_minutos=tempo))
    for numero, (prazo, pendente) in enumerate(pecas):
        os.incluir_peca(
            criar_peca(codigo_referencia=f"P-{numero}", prazo_reposicao_dias=prazo), quantidade=2
        )
        os.pecas[numero].quantidade_pendente = pendente
        os.pecas[numero].quantidade_reservada = 2 - pendente
    os.status = status
    for campo, valor in alteracoes.items():
        setattr(os, campo, valor)
    return os


@pytest.mark.parametrize("status", [StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO, StatusOS.CANCELADA])
def test_nao_estima_a_entrega_antes_da_definicao_dos_servicos_nem_se_cancelada(status):
    os = os_com_itens(status, minutos=(60,), pecas=((3, 1),))

    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) is None


@pytest.mark.parametrize("status", [StatusOS.AGUARDANDO_APROVACAO, StatusOS.AGUARDANDO_PECA])
def test_aguardando_aprovacao_ou_peca_soma_consulta_prazo_das_pecas_e_duracao(status):
    os = os_com_itens(status, minutos=(60, 120), pecas=((3, 1), (5, 2)))

    estimativa = os.estimar_entrega(MOMENTO_DA_CONSULTA)

    assert estimativa == MOMENTO_DA_CONSULTA + timedelta(days=5, hours=3)


def test_aguardando_execucao_soma_consulta_e_duracao_ignorando_o_prazo_das_pecas():
    os = os_com_itens(StatusOS.AGUARDANDO_EXECUCAO, minutos=(60, 120), pecas=((9, 1),))

    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == MOMENTO_DA_CONSULTA + timedelta(hours=3)


def test_em_execucao_soma_o_inicio_da_execucao_e_a_duracao_sem_usar_a_consulta():
    inicio = MOMENTO_DA_CONSULTA - timedelta(hours=2)
    os = os_com_itens(StatusOS.EM_EXECUCAO, minutos=(60, 120), data_inicio_execucao=inicio)

    esperada = inicio + timedelta(hours=3)
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == esperada
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA + timedelta(days=9)) == esperada


@pytest.mark.parametrize("status", [StatusOS.FINALIZADA, StatusOS.ENTREGUE])
def test_finalizada_ou_entregue_devolve_a_data_de_finalizacao(status):
    finalizacao = MOMENTO_DA_CONSULTA - timedelta(days=1)
    os = os_com_itens(status, minutos=(60,), data_finalizacao=finalizacao)

    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == finalizacao


def test_o_prazo_das_pecas_e_o_maior_entre_as_pendentes():
    os = os_com_itens(StatusOS.AGUARDANDO_PECA, pecas=((2, 1), (7, 2), (4, 1)))

    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == MOMENTO_DA_CONSULTA + timedelta(days=7)


def test_peca_ja_reservada_nao_conta_para_o_prazo():
    os = os_com_itens(StatusOS.AGUARDANDO_APROVACAO, pecas=((9, 0), (2, 1)))

    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == MOMENTO_DA_CONSULTA + timedelta(days=2)


def test_sem_pecas_pendentes_o_prazo_das_pecas_e_zero():
    os = os_com_itens(StatusOS.AGUARDANDO_APROVACAO, minutos=(30,), pecas=((9, 0),))

    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == MOMENTO_DA_CONSULTA + timedelta(minutes=30)


def test_os_sem_servicos_tem_duracao_zero():
    os = os_com_itens(StatusOS.AGUARDANDO_EXECUCAO)

    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == MOMENTO_DA_CONSULTA


def test_a_estimativa_usa_os_valores_congelados_e_nao_os_do_catalogo():
    servico = criar_servico(tempo_estimado_minutos=60)
    peca = criar_peca(prazo_reposicao_dias=3)
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)
    os.finalizar_orcamento(USUARIO_ID, [servico], [peca])
    servico.atualizar_dados(
        codigo=servico.codigo,
        nome=servico.nome,
        descricao=servico.descricao,
        valor_base=servico.valor_base,
        tempo_estimado_minutos=600,
    )
    peca.atualizar_dados(
        codigo_referencia=peca.codigo_referencia,
        nome=peca.nome,
        preco_unitario=peca.preco_unitario,
        prazo_reposicao_dias=30,
    )

    estimativa = os.estimar_entrega(MOMENTO_DA_CONSULTA)

    assert estimativa == MOMENTO_DA_CONSULTA + timedelta(days=3, hours=1)


@pytest.mark.parametrize(
    "momento",
    [datetime(2026, 10, 27, 12, 0), "2026-10-27", None, 1_800_000_000],
    ids=["sem fuso", "texto", "nulo", "numero"],
)
def test_recusa_momento_da_consulta_sem_fuso_horario_mesmo_nos_status_que_o_ignoram(momento):
    os = os_com_itens(StatusOS.EM_DIAGNOSTICO)

    with pytest.raises(OrdemServicoInvalida):
        os.estimar_entrega(momento)


def test_os_em_execucao_sem_inicio_registrado_e_recusada():
    os = os_com_itens(StatusOS.EM_EXECUCAO, minutos=(60,))

    with pytest.raises(OrdemServicoInvalida, match="início da execução"):
        os.estimar_entrega(MOMENTO_DA_CONSULTA)


@pytest.mark.parametrize("status", [StatusOS.FINALIZADA, StatusOS.ENTREGUE])
def test_os_finalizada_ou_entregue_sem_finalizacao_registrada_e_recusada(status):
    os = os_com_itens(status)

    with pytest.raises(OrdemServicoInvalida, match="finalização"):
        os.estimar_entrega(MOMENTO_DA_CONSULTA)


def test_prazos_que_estouram_o_limite_de_datas_viram_erro_de_dominio():
    os = os_com_itens(StatusOS.AGUARDANDO_EXECUCAO, minutos=(10**13,))

    with pytest.raises(OrdemServicoInvalida, match="limite de datas"):
        os.estimar_entrega(MOMENTO_DA_CONSULTA)


def test_a_estimativa_acompanha_o_fluxo_real_da_os():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    servico = criar_servico(tempo_estimado_minutos=90)
    peca = criar_peca(prazo_reposicao_dias=4)
    os = criar_os(status=StatusOS.RECEBIDA, mecanico_id=None)
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) is None

    os.atribuir_mecanico(mecanico, mecanico)
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=1)
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) is None

    os.finalizar_orcamento(mecanico.id, [servico], [peca])
    esperada = MOMENTO_DA_CONSULTA + timedelta(days=4, minutes=90)
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == esperada

    os.aprovar_orcamento()
    assert os.status is StatusOS.AGUARDANDO_PECA
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == esperada

    os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente = 1, 0
    os.liberar_para_execucao()
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == MOMENTO_DA_CONSULTA + timedelta(minutes=90)

    os.iniciar_execucao(mecanico)
    previsto_a_partir_do_inicio = os.data_inicio_execucao + timedelta(minutes=90)
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == previsto_a_partir_do_inicio

    os.concluir_manutencao(mecanico)
    assert os.estimar_entrega(MOMENTO_DA_CONSULTA) == os.data_finalizacao


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


def item_peca_reservado(quantidade: int, reservada: int, pendente: int = 0) -> ItemPeca:
    return ItemPeca(
        peca_id=uuid4(),
        nome="Filtro de óleo",
        quantidade=quantidade,
        preco_unitario_congelado=Valor("35.90"),
        prazo_reposicao_dias=3,
        quantidade_reservada=reservada,
        quantidade_pendente=pendente,
    )


def test_os_nova_nao_tem_eventos_acumulados():
    assert criar_os().collect_domain_events() == []


def test_finalizar_orcamento_acumula_orcamento_finalizado():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=2)

    os.finalizar_orcamento(USUARIO_ID, [], [peca])

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, OrcamentoFinalizadoEvent)
    assert evento.os_id == os.id


def test_finalizar_orcamento_recusado_nao_acumula_evento():
    os = criar_os(status=StatusOS.RECEBIDA)

    with pytest.raises(TransicaoDeStatusInvalida):
        os.finalizar_orcamento(USUARIO_ID, [], [])

    assert os.collect_domain_events() == []


def test_rejeitar_orcamento_acumula_os_cancelada_com_as_quantidades_reservadas():
    os = os_aguardando_aprovacao_com_peca_pendente()
    os.collect_domain_events()

    os.rejeitar_orcamento()

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, OSCanceladaEvent)
    assert evento.os_id == os.id
    assert evento.estornos == [QuantidadePeca(os.pecas[0].peca_id, 1)]


def test_rejeitar_orcamento_sem_reservas_acumula_os_cancelada_sem_estornos():
    os = criar_os(status=StatusOS.AGUARDANDO_APROVACAO)

    os.rejeitar_orcamento()

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, OSCanceladaEvent)
    assert evento.estornos == []


def test_cancelar_acumula_os_cancelada_com_as_quantidades_reservadas_de_cada_peca():
    inteiro, parcial = item_peca_reservado(2, reservada=2), item_peca_reservado(3, 1, pendente=2)
    sem_reserva = item_peca_reservado(4, reservada=0, pendente=4)
    os = criar_os(status=StatusOS.AGUARDANDO_PECA, pecas=[inteiro, parcial, sem_reserva])

    os.cancelar(USUARIO_ID, "Cliente desistiu do serviço")

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, OSCanceladaEvent)
    assert evento.os_id == os.id
    assert evento.estornos == [
        QuantidadePeca(inteiro.peca_id, 2),
        QuantidadePeca(parcial.peca_id, 1),
    ]


@pytest.mark.parametrize("status", [StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO])
def test_cancelar_antes_do_orcamento_acumula_os_cancelada_sem_estornos(status):
    os = criar_os(status=status)

    os.cancelar(USUARIO_ID, "Cliente desistiu do serviço")

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, OSCanceladaEvent)
    assert evento.estornos == []


def test_cancelar_em_execucao_acumula_os_cancelada_com_estornos_vazios():
    item = item_peca_reservado(2, reservada=2)
    os = criar_os(status=StatusOS.EM_EXECUCAO, pecas=[item])

    os.cancelar(USUARIO_ID, "Peça com defeito de fábrica")

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, OSCanceladaEvent)
    assert evento.os_id == os.id
    assert evento.estornos == []


def test_cancelamento_recusado_nao_acumula_evento():
    os = criar_os(status=StatusOS.EM_DIAGNOSTICO)

    with pytest.raises(MotivoObrigatorio):
        os.cancelar(USUARIO_ID, "  ")
    os.status = StatusOS.ENTREGUE
    with pytest.raises(TransicaoDeStatusInvalida):
        os.cancelar(USUARIO_ID, "Tarde demais")

    assert os.collect_domain_events() == []


def test_iniciar_execucao_acumula_execucao_iniciada_com_as_quantidades_reservadas():
    primeira, segunda = item_peca_reservado(2, reservada=2), item_peca_reservado(1, reservada=1)
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(
        status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=mecanico.id, pecas=[primeira, segunda]
    )

    os.iniciar_execucao(mecanico)

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, ExecucaoIniciadaEvent)
    assert evento.os_id == os.id
    assert evento.baixas == [
        QuantidadePeca(primeira.peca_id, 2),
        QuantidadePeca(segunda.peca_id, 1),
    ]


def test_iniciar_execucao_sem_pecas_acumula_execucao_iniciada_sem_baixas():
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO)

    os.iniciar_execucao(criar_usuario(PerfilUsuario.GERENTE))

    (evento,) = os.collect_domain_events()
    assert isinstance(evento, ExecucaoIniciadaEvent)
    assert evento.baixas == []


def test_iniciar_execucao_recusada_nao_acumula_evento():
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=uuid4())

    with pytest.raises(AcessoNegado):
        os.iniciar_execucao(criar_usuario(PerfilUsuario.MECANICO))

    assert os.collect_domain_events() == []


def test_transicoes_sem_reacao_no_estoque_nao_acumulam_evento():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    os = criar_os(status=StatusOS.RECEBIDA)
    os.atribuir_mecanico(mecanico, mecanico)
    aguardando_peca = os_aguardando_aprovacao_com_peca_pendente()
    aguardando_peca.collect_domain_events()

    aguardando_peca.aprovar_orcamento()
    aguardando_peca.pecas[0].quantidade_reservada = 2
    aguardando_peca.pecas[0].quantidade_pendente = 0
    aguardando_peca.liberar_para_execucao()
    em_execucao = criar_os(status=StatusOS.EM_EXECUCAO)
    em_execucao.concluir_manutencao(criar_usuario(PerfilUsuario.GERENTE))
    em_execucao.entregar_veiculo(USUARIO_ID)

    for ordem in (os, aguardando_peca, em_execucao):
        assert ordem.collect_domain_events() == []


def test_collect_domain_events_devolve_na_ordem_e_esvazia_a_lista():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    item = item_peca_reservado(1, reservada=1)
    os = criar_os(status=StatusOS.AGUARDANDO_EXECUCAO, mecanico_id=mecanico.id, pecas=[item])
    os.iniciar_execucao(mecanico)
    os.cancelar(USUARIO_ID, "Peça com defeito de fábrica")

    eventos = os.collect_domain_events()

    assert [type(evento) for evento in eventos] == [ExecucaoIniciadaEvent, OSCanceladaEvent]
    assert os.collect_domain_events() == []


def os_aguardando_peca(*itens: ItemPeca, **alteracoes) -> OrdemServico:
    return criar_os(status=StatusOS.AGUARDANDO_PECA, pecas=list(itens), **alteracoes)


def test_alocar_peca_converte_a_pendente_em_reservada_e_mantem_a_os_aguardando_peca():
    item, outro = item_peca_reservado(3, 1, pendente=2), item_peca_reservado(1, 0, pendente=1)
    os = os_aguardando_peca(item, outro)

    os.alocar_peca(item.peca_id, 1)

    assert (item.quantidade_reservada, item.quantidade_pendente) == (2, 1)
    assert (outro.quantidade_reservada, outro.quantidade_pendente) == (0, 1)
    assert os.status is StatusOS.AGUARDANDO_PECA


def test_alocar_peca_libera_a_os_em_aguardando_peca_quando_nao_resta_pendencia():
    item = item_peca_reservado(3, 1, pendente=2)
    os = os_aguardando_peca(item)

    os.alocar_peca(item.peca_id, 2)

    assert (item.quantidade_reservada, item.quantidade_pendente) == (3, 0)
    assert os.status is StatusOS.AGUARDANDO_EXECUCAO
    registro = os.historico[-1]
    assert (registro.status_anterior, registro.status_novo) == (
        StatusOS.AGUARDANDO_PECA,
        StatusOS.AGUARDANDO_EXECUCAO,
    )
    assert registro.origem is OrigemTransicao.SISTEMA
    assert registro.usuario_id is None


def test_alocar_peca_so_libera_a_os_quando_a_ultima_peca_pendente_e_alocada():
    primeira, segunda = item_peca_reservado(2, 0, pendente=2), item_peca_reservado(1, 0, pendente=1)
    os = os_aguardando_peca(primeira, segunda)

    os.alocar_peca(primeira.peca_id, 2)
    assert os.status is StatusOS.AGUARDANDO_PECA

    os.alocar_peca(segunda.peca_id, 1)
    assert os.status is StatusOS.AGUARDANDO_EXECUCAO


def test_alocar_peca_em_aguardando_aprovacao_reserva_sem_mudar_o_status():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=2)
    os.finalizar_orcamento(USUARIO_ID, [], [peca])

    os.alocar_peca(peca.id, 2)

    assert os.status is StatusOS.AGUARDANDO_APROVACAO
    assert (os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente) == (2, 0)
    os.aprovar_orcamento()
    assert os.status is StatusOS.AGUARDANDO_EXECUCAO


def test_alocar_peca_nao_acumula_evento_de_dominio():
    item = item_peca_reservado(1, 0, pendente=1)
    os = os_aguardando_peca(item)

    os.alocar_peca(item.peca_id, 1)

    assert os.collect_domain_events() == []


def test_alocar_peca_que_nao_esta_na_os_nao_altera_nada():
    item = item_peca_reservado(1, 0, pendente=1)
    os = os_aguardando_peca(item)

    with pytest.raises(EntidadeNaoEncontrada):
        os.alocar_peca(uuid4(), 1)

    assert (item.quantidade_reservada, item.quantidade_pendente) == (0, 1)
    assert os.status is StatusOS.AGUARDANDO_PECA


@pytest.mark.parametrize("quantidade", [0, -1, 3, True, 1.5, None])
def test_alocar_peca_com_quantidade_invalida_ou_acima_da_pendente_nao_altera_nada(quantidade):
    item = item_peca_reservado(3, 1, pendente=2)
    os = os_aguardando_peca(item)

    with pytest.raises(OrdemServicoInvalida):
        os.alocar_peca(item.peca_id, quantidade)

    assert (item.quantidade_reservada, item.quantidade_pendente) == (1, 2)
    assert os.status is StatusOS.AGUARDANDO_PECA
    assert os.historico == ()


def test_reposicao_insuficiente_libera_so_a_os_mais_antiga_e_a_mais_nova_segue_aguardando():
    peca = criar_peca()
    abertura = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)

    def os_aguardando(data_abertura: datetime) -> OrdemServico:
        item = ItemPeca.a_partir_de(peca, quantidade=3)
        item.marcar_como_pendente()
        return os_aguardando_peca(item, data_abertura=data_abertura)

    antiga, nova = os_aguardando(abertura), os_aguardando(abertura + timedelta(hours=2))
    estoque = EstoquePeca(peca_id=peca.id, quantidade_fisica=4)
    ordens = {antiga.id: antiga, nova.id: nova}

    alocacoes = estoque.alocar_pendencias(
        [
            PendenciaPeca(nova.id, nova.data_abertura, nova.pecas[0].quantidade_pendente),
            PendenciaPeca(antiga.id, antiga.data_abertura, antiga.pecas[0].quantidade_pendente),
        ]
    )
    for alocacao in alocacoes:
        ordens[alocacao.os_id].alocar_peca(peca.id, alocacao.quantidade_reservada)

    assert [(a.os_id, a.quantidade_reservada) for a in alocacoes] == [(antiga.id, 3), (nova.id, 1)]
    assert antiga.status is StatusOS.AGUARDANDO_EXECUCAO
    assert nova.status is StatusOS.AGUARDANDO_PECA
    assert (nova.pecas[0].quantidade_reservada, nova.pecas[0].quantidade_pendente) == (1, 2)
    assert estoque.saldo_disponivel() == 0
