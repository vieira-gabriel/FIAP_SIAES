from datetime import UTC, datetime

import pytest

from application.use_cases.criar_carga_inicial import CriarCargaInicial, SenhasDaCargaInicial
from application.use_cases.criar_dados_de_demonstracao import CriarDadosDeDemonstracao
from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.servico import Servico
from domain.entities.veiculo import Veiculo
from domain.value_objects.documento import Documento
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

MOMENTO = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
_RESERVAM_SALDO = {
    StatusOS.AGUARDANDO_APROVACAO,
    StatusOS.AGUARDANDO_PECA,
    StatusOS.AGUARDANDO_EXECUCAO,
}


@pytest.fixture
async def demonstracao(
    usuarios, password_hasher, servicos, pecas, estoques, clientes, veiculos, ordens
):
    await CriarCargaInicial(usuarios, password_hasher).executar(
        SenhasDaCargaInicial(gerente="senha-admin", atendente="senha-at", mecanico="senha-mec")
    )
    return CriarDadosDeDemonstracao(usuarios, servicos, pecas, estoques, clientes, veiculos, ordens)


def _por_status(ordens) -> dict[StatusOS, list[OrdemServico]]:
    agrupadas = {}
    for os in ordens.dados.values():
        agrupadas.setdefault(os.status, []).append(os)
    return agrupadas


async def test_cria_cinco_servicos_e_tres_pecas_com_estoque(
    demonstracao, servicos, pecas, estoques
):
    await demonstracao.executar(MOMENTO)

    assert len(servicos.dados) == 5
    assert len(pecas.dados) == 3
    assert set(estoques.dados) == set(pecas.dados)


async def test_cria_ao_menos_uma_os_em_cada_status(demonstracao, ordens):
    await demonstracao.executar(MOMENTO)

    assert set(_por_status(ordens)) == set(StatusOS)


async def test_historico_encadeado_no_passado_e_em_ordem(demonstracao, ordens):
    await demonstracao.executar(MOMENTO)

    for os in ordens.dados.values():
        datas = [registro.data_hora for registro in os.historico]
        assert datas == sorted(datas)
        assert datas[0] == os.data_abertura
        assert datas[-1] < MOMENTO
        assert os.historico[0].status_anterior is None
        assert os.historico[-1].status_novo is os.status


async def test_transicoes_tem_a_origem_e_o_responsavel_de_cada_perfil(
    demonstracao, ordens, usuarios
):
    await demonstracao.executar(MOMENTO)
    atendente = await usuarios.buscar_por_email("atendente@oficina.com")
    mecanico = await usuarios.buscar_por_email("mecanico@oficina.com")

    registros = [r for os in ordens.dados.values() for r in os.historico]
    responsaveis = {
        r.status_novo: r.usuario_id for r in registros if r.origem is OrigemTransicao.USUARIO
    }
    assert responsaveis[StatusOS.RECEBIDA] == atendente.id
    assert responsaveis[StatusOS.ENTREGUE] == atendente.id
    assert responsaveis[StatusOS.EM_EXECUCAO] == mecanico.id
    origens = {r.origem for r in registros}
    assert origens == set(OrigemTransicao)


async def test_datas_de_execucao_e_finalizacao_seguem_o_historico(demonstracao, ordens):
    await demonstracao.executar(MOMENTO)

    for os in ordens.dados.values():
        executou = os.status in {StatusOS.EM_EXECUCAO, StatusOS.FINALIZADA, StatusOS.ENTREGUE}
        finalizou = os.status in {StatusOS.FINALIZADA, StatusOS.ENTREGUE}
        assert (os.data_inicio_execucao is not None) == executou
        assert (os.data_finalizacao is not None) == finalizou
        if finalizou:
            assert os.tempo_de_execucao().total_seconds() > 0


async def test_relatorio_de_tempos_tem_espera_por_peca_e_meses_diferentes(demonstracao, ordens):
    await demonstracao.executar(MOMENTO)

    entregues = _por_status(ordens)[StatusOS.ENTREGUE]
    assert any(os.tempo_de_espera_por_peca() for os in entregues)
    assert len({os.data_finalizacao.strftime("%Y-%m") for os in entregues}) == 2


async def test_orcamento_existe_a_partir_da_conclusao(demonstracao, ordens):
    await demonstracao.executar(MOMENTO)

    for status, lista in _por_status(ordens).items():
        tem_orcamento = status not in {StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO}
        assert all((os.orcamento is not None) == tem_orcamento for os in lista)


async def test_reservas_do_estoque_conferem_com_as_os(demonstracao, ordens, estoques):
    await demonstracao.executar(MOMENTO)

    for peca_id, estoque in estoques.dados.items():
        reservada_nas_os = sum(
            item.quantidade_reservada
            for os in ordens.dados.values()
            if os.status in _RESERVAM_SALDO
            for item in os.pecas
            if item.peca_id == peca_id
        )
        assert estoque.quantidade_reservada == reservada_nas_os
        assert estoque.saldo_disponivel() >= 0


async def test_os_aguardando_peca_tem_pendencia_sem_saldo(demonstracao, ordens, estoques):
    await demonstracao.executar(MOMENTO)

    (os,) = _por_status(ordens)[StatusOS.AGUARDANDO_PECA]
    pendentes = [item for item in os.pecas if item.quantidade_pendente > 0]
    assert pendentes
    assert all(estoques.dados[item.peca_id].saldo_disponivel() == 0 for item in pendentes)
    for status in (StatusOS.AGUARDANDO_EXECUCAO, StatusOS.EM_EXECUCAO, StatusOS.ENTREGUE):
        for outra in _por_status(ordens)[status]:
            assert all(item.quantidade_pendente == 0 for item in outra.pecas)


async def test_executar_de_novo_nao_duplica(demonstracao, servicos, pecas, clientes, ordens):
    await demonstracao.executar(MOMENTO)
    quantidades = (len(servicos.dados), len(pecas.dados), len(clientes.dados), len(ordens.dados))

    await demonstracao.executar(MOMENTO)

    assert (len(servicos.dados), len(pecas.dados), len(clientes.dados), len(ordens.dados)) == (
        quantidades
    )


async def test_com_os_ja_cadastrada_cria_so_o_catalogo(demonstracao, servicos, ordens):
    await demonstracao.executar(MOMENTO)
    existente = next(iter(ordens.dados.values()))
    ordens.dados = {existente.id: existente}
    servicos.dados.clear()

    await demonstracao.executar(MOMENTO)

    assert len(servicos.dados) == 5
    assert list(ordens.dados) == [existente.id]


async def test_servico_com_o_mesmo_codigo_e_reaproveitado(demonstracao, servicos, ordens):
    existente = Servico("SRV-OLEO", "Óleo da casa", "Troca de óleo.", Valor("99.00"), 30)
    await servicos.salvar(existente)

    await demonstracao.executar(MOMENTO)

    assert len(servicos.dados) == 5
    assert servicos.dados[existente.id].valor_base == Valor("99.00")
    nomes = {item.nome for os in ordens.dados.values() for item in os.servicos}
    assert "Óleo da casa" in nomes


async def test_cliente_com_o_mesmo_documento_e_reaproveitado(demonstracao, clientes, ordens):
    existente = Cliente(
        nome="Ana da Casa",
        documento=Documento.de_texto("529.982.247-25"),
        email="ana@casa.com",
        telefone="11900000000",
    )
    await clientes.salvar(existente)

    await demonstracao.executar(MOMENTO)

    assert len(clientes.dados) == 5
    assert clientes.dados[existente.id].nome == "Ana da Casa"
    nomes = {os.cliente_id for os in ordens.dados.values()}
    assert existente.id in nomes


async def test_veiculo_com_a_mesma_placa_e_reaproveitado(demonstracao, clientes, veiculos, ordens):
    dono = Cliente(
        nome="Ana da Casa",
        documento=Documento.de_texto("529.982.247-25"),
        email="ana@casa.com",
        telefone="11900000000",
    )
    await clientes.salvar(dono)
    existente = Veiculo(
        cliente_id=dono.id, placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2010
    )
    await veiculos.salvar(existente)

    await demonstracao.executar(MOMENTO)

    assert len(veiculos.dados) == 5
    assert veiculos.dados[existente.id].modelo == "Uno"
    assert existente.id in {os.veiculo_id for os in ordens.dados.values()}


async def test_veiculo_com_a_placa_de_outro_cliente_fica_sem_os(
    demonstracao, clientes, veiculos, ordens
):
    outro = Cliente(
        nome="Pedro de Fora",
        documento=Documento.de_texto("123.456.789-09"),
        email="pedro@fora.com",
        telefone="11900000001",
    )
    await clientes.salvar(outro)
    do_outro = Veiculo(
        cliente_id=outro.id, placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2010
    )
    await veiculos.salvar(do_outro)

    await demonstracao.executar(MOMENTO)

    assert do_outro.id not in {os.veiculo_id for os in ordens.dados.values()}
    assert len(ordens.dados) == 8
    for os in ordens.dados.values():
        assert veiculos.dados[os.veiculo_id].cliente_id == os.cliente_id
