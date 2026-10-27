from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.entities.usuario import Usuario
from domain.exceptions import (
    AcessoNegado,
    EntidadeNaoEncontrada,
    ItemIndisponivel,
    ItemJaIncluido,
    ItensBloqueados,
    MotivoObrigatorio,
    OrdemServicoInvalida,
    PecasPendentes,
    TransicaoDeStatusInvalida,
    ValorInvalido,
)
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.orcamento import Orcamento
from domain.value_objects.perfil_usuario import PerfilUsuario
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


def fora_de(*permitidos: StatusOS) -> list[StatusOS]:
    return [status for status in StatusOS if status not in permitidos]


def test_atribuir_mecanico_leva_a_os_para_em_diagnostico():
    mecanico_id = uuid4()
    os = criar_os(status=StatusOS.RECEBIDA)

    os.atribuir_mecanico(mecanico_id)

    assert os.status is StatusOS.EM_DIAGNOSTICO
    assert os.mecanico_id == mecanico_id


@pytest.mark.parametrize("status", fora_de(StatusOS.RECEBIDA))
def test_atribuir_mecanico_so_a_partir_de_recebida(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.atribuir_mecanico(uuid4())

    assert erro.value.status_atual is status
    assert erro.value.status_pretendido is StatusOS.EM_DIAGNOSTICO
    assert os.status is status
    assert os.mecanico_id is None


@pytest.mark.parametrize("mecanico_id", ["nao-e-uuid", None, 123])
def test_atribuir_mecanico_recusa_id_invalido_sem_mudar_o_status(mecanico_id):
    os = criar_os(status=StatusOS.RECEBIDA)

    with pytest.raises(OrdemServicoInvalida):
        os.atribuir_mecanico(mecanico_id)

    assert os.status is StatusOS.RECEBIDA
    assert os.mecanico_id is None


def test_finalizar_orcamento_congela_os_valores_vigentes_e_aguarda_a_aprovacao():
    servico, peca = criar_servico(valor_base=Valor("120.00")), criar_peca()
    os = criar_os()
    os.incluir_servico(servico)
    os.incluir_peca(peca, quantidade=2)
    reajustar_servico(servico, "150.00")

    os.finalizar_orcamento([servico], [peca])

    assert os.status is StatusOS.AGUARDANDO_APROVACAO
    assert os.orcamento.total == Valor("221.80")


@pytest.mark.parametrize("status", fora_de(StatusOS.EM_DIAGNOSTICO))
def test_finalizar_orcamento_so_a_partir_de_em_diagnostico(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.finalizar_orcamento([], [])

    assert erro.value.status_pretendido is StatusOS.AGUARDANDO_APROVACAO
    assert os.status is status
    assert os.orcamento is None


def test_finalizar_orcamento_sem_valor_vigente_mantem_o_diagnostico():
    os = criar_os()
    os.incluir_peca(criar_peca(), quantidade=1)

    with pytest.raises(OrdemServicoInvalida):
        os.finalizar_orcamento([], [])

    assert os.status is StatusOS.EM_DIAGNOSTICO
    assert os.orcamento is None


def criar_usuario(perfil: PerfilUsuario) -> Usuario:
    return Usuario(nome="Ana", email="ana@oficina.com", senha_hash="hash", perfil=perfil)


def os_aguardando_aprovacao_com_peca_pendente() -> OrdemServico:
    """Duas unidades da peça: uma reservada e uma pendente."""
    peca = criar_peca()
    os = criar_os(status=StatusOS.EM_DIAGNOSTICO)
    os.incluir_peca(peca, quantidade=2)
    os.finalizar_orcamento([], [peca])
    os.pecas[0].quantidade_reservada = 1
    os.pecas[0].quantidade_pendente = 1
    return os


def test_aprovar_orcamento_sem_pecas_pendentes_aguarda_a_execucao():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=2)
    os.finalizar_orcamento([], [peca])
    os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente = 2, 0

    os.aprovar_orcamento()

    assert os.status is StatusOS.AGUARDANDO_EXECUCAO


def test_finalizar_orcamento_deixa_toda_a_quantidade_das_pecas_pendente_de_reserva():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=3)

    os.finalizar_orcamento([], [peca])

    assert (os.pecas[0].quantidade_reservada, os.pecas[0].quantidade_pendente) == (0, 3)


def test_aprovar_antes_da_reserva_de_estoque_aguarda_a_peca():
    peca = criar_peca()
    os = criar_os()
    os.incluir_peca(peca, quantidade=1)
    os.finalizar_orcamento([], [peca])

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

    os.cancelar("Cliente desistiu do serviço")

    assert os.status is StatusOS.CANCELADA


@pytest.mark.parametrize("status", [StatusOS.FINALIZADA, StatusOS.ENTREGUE, StatusOS.CANCELADA])
def test_nao_cancela_os_finalizada_entregue_ou_cancelada(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.cancelar("Qualquer motivo")

    assert erro.value.status_pretendido is StatusOS.CANCELADA
    assert os.status is status


@pytest.mark.parametrize("motivo", ["", "   ", None])
def test_cancelar_exige_o_motivo(motivo):
    os = criar_os(status=StatusOS.AGUARDANDO_PECA)

    with pytest.raises(MotivoObrigatorio):
        os.cancelar(motivo)

    assert os.status is StatusOS.AGUARDANDO_PECA


def test_fluxo_completo_sem_pecas_pendentes():
    mecanico = criar_usuario(PerfilUsuario.MECANICO)
    servico = criar_servico()
    os = criar_os(status=StatusOS.RECEBIDA)

    os.atribuir_mecanico(mecanico.id)
    os.incluir_servico(servico)
    os.finalizar_orcamento([servico], [])
    os.aprovar_orcamento()
    os.iniciar_execucao(mecanico)
    os.concluir_manutencao()
    os.entregar_veiculo()

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

    os.concluir_manutencao()

    assert os.status is StatusOS.FINALIZADA
    assert os.data_finalizacao.tzinfo is UTC
    assert antes <= os.data_finalizacao <= antes + timedelta(seconds=1)


@pytest.mark.parametrize("status", fora_de(StatusOS.EM_EXECUCAO))
def test_concluir_manutencao_so_a_partir_de_em_execucao(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.concluir_manutencao()

    assert erro.value.status_pretendido is StatusOS.FINALIZADA
    assert os.status is status
    assert os.data_finalizacao is None


def test_itens_ficam_bloqueados_depois_de_finalizada():
    os = criar_os(status=StatusOS.EM_EXECUCAO)
    os.concluir_manutencao()

    with pytest.raises(ItensBloqueados) as erro:
        os.incluir_servico(criar_servico())

    assert erro.value.status_atual is StatusOS.FINALIZADA


def test_entregar_veiculo_leva_a_os_finalizada_para_entregue():
    os = criar_os(status=StatusOS.FINALIZADA)

    os.entregar_veiculo()

    assert os.status is StatusOS.ENTREGUE


@pytest.mark.parametrize("status", fora_de(StatusOS.FINALIZADA))
def test_entregar_veiculo_so_a_partir_de_finalizada(status):
    os = criar_os(status=status)

    with pytest.raises(TransicaoDeStatusInvalida) as erro:
        os.entregar_veiculo()

    assert erro.value.status_pretendido is StatusOS.ENTREGUE
    assert os.status is status


def test_a_os_abre_sem_mecanico_e_sem_timestamps_de_execucao():
    os = criar_os(status=StatusOS.RECEBIDA)

    assert os.mecanico_id is None
    assert os.data_inicio_execucao is None
    assert os.data_finalizacao is None


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
