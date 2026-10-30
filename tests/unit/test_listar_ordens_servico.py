from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application.use_cases.listar_ordens_servico import CriteriosDaListagem, ListarOrdensServico
from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.cpf import CPF
from domain.value_objects.documento import Documento
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS

CPF_MARIA = "52998224725"
CPF_JOSE = "11144477735"


async def _cliente_com_veiculo(clientes, veiculos, cpf: str, placa: str):
    cliente = Cliente(
        nome=f"Cliente {cpf[-2:]}", documento=CPF(cpf), email="c@e.com", telefone="11"
    )
    veiculo = Veiculo(
        cliente_id=cliente.id, placa=Placa(placa), marca="Fiat", modelo="Uno", ano=2015
    )
    await clientes.salvar(cliente)
    await veiculos.salvar(veiculo)
    return cliente, veiculo


async def _os(ordens, numero: str, cliente, veiculo, mecanico: Usuario | None = None):
    os = OrdemServico.abrir(
        numero=NumeroOS(numero),
        cliente_id=cliente.id,
        veiculo_id=veiculo.id,
        atendente_id=uuid4(),
    )
    if mecanico is not None:
        os.atribuir_mecanico(mecanico.id)
    await ordens.salvar(os)
    return os


@pytest.fixture
async def cenario(clientes, veiculos, ordens, usuarios):
    maria, veiculo_maria = await _cliente_com_veiculo(clientes, veiculos, CPF_MARIA, "ABC1D23")
    jose, veiculo_jose = await _cliente_com_veiculo(clientes, veiculos, CPF_JOSE, "DEF2G34")
    mecanico = Usuario(
        nome="Pedro", email="p@oficina.com", senha_hash="h", perfil=PerfilUsuario.MECANICO
    )
    await usuarios.salvar(mecanico)
    recebida = await _os(ordens, "529-7F3A9C2B", maria, veiculo_maria)
    em_diagnostico = await _os(ordens, "111-0A1B2C3D", jose, veiculo_jose, mecanico=mecanico)
    return {
        "recebida": recebida,
        "em_diagnostico": em_diagnostico,
        "mecanico": mecanico,
        "jose": jose,
        "veiculo_jose": veiculo_jose,
    }


def _listar(clientes, veiculos, ordens, usuarios, **criterios):
    return ListarOrdensServico(ordens, clientes, veiculos, usuarios).executar(
        CriteriosDaListagem(**criterios)
    )


async def test_sem_criterios_lista_todas_as_os(clientes, veiculos, ordens, usuarios, cenario):
    resumos = await _listar(clientes, veiculos, ordens, usuarios)

    assert {r.os.id for r in resumos} == {cenario["recebida"].id, cenario["em_diagnostico"].id}


async def test_resumo_traz_cliente_veiculo_e_mecanico(
    clientes, veiculos, ordens, usuarios, cenario
):
    resumos = await _listar(clientes, veiculos, ordens, usuarios, status=StatusOS.EM_DIAGNOSTICO)

    (resumo,) = resumos
    assert resumo.cliente == cenario["jose"]
    assert resumo.veiculo == cenario["veiculo_jose"]
    assert resumo.mecanico == cenario["mecanico"]


async def test_filtra_por_status(clientes, veiculos, ordens, usuarios, cenario):
    resumos = await _listar(clientes, veiculos, ordens, usuarios, status=StatusOS.RECEBIDA)

    assert [r.os.id for r in resumos] == [cenario["recebida"].id]


async def test_filtra_por_mecanico(clientes, veiculos, ordens, usuarios, cenario):
    resumos = await _listar(
        clientes, veiculos, ordens, usuarios, mecanico_id=cenario["mecanico"].id
    )

    assert [r.os.id for r in resumos] == [cenario["em_diagnostico"].id]
    assert resumos[0].mecanico == cenario["mecanico"]


async def test_filtra_pelo_documento_do_cliente(clientes, veiculos, ordens, usuarios, cenario):
    resumos = await _listar(
        clientes, veiculos, ordens, usuarios, documento=Documento.de_texto(CPF_MARIA)
    )

    assert [r.os.id for r in resumos] == [cenario["recebida"].id]


async def test_filtra_pela_placa_do_veiculo(clientes, veiculos, ordens, usuarios, cenario):
    resumos = await _listar(clientes, veiculos, ordens, usuarios, placa=Placa("DEF2G34"))

    assert [r.os.id for r in resumos] == [cenario["em_diagnostico"].id]


async def test_a_placa_de_veiculo_excluido_continua_listando_as_os_dele(
    clientes, veiculos, ordens, usuarios, cenario
):
    cenario["veiculo_jose"].excluir()
    await veiculos.salvar(cenario["veiculo_jose"])

    resumos = await _listar(clientes, veiculos, ordens, usuarios, placa=Placa("DEF2G34"))

    assert [r.os.id for r in resumos] == [cenario["em_diagnostico"].id]


async def test_placa_reaproveitada_lista_as_os_do_veiculo_antigo_e_do_novo(
    clientes, veiculos, ordens, usuarios, cenario
):
    cenario["veiculo_jose"].excluir()
    await veiculos.salvar(cenario["veiculo_jose"])
    maria = await clientes.buscar_por_documento(Documento.de_texto(CPF_MARIA))
    novo = Veiculo(
        cliente_id=maria.id, placa=Placa("DEF2G34"), marca="VW", modelo="Gol", ano=2020
    )
    await veiculos.salvar(novo)
    os_do_novo = await _os(ordens, "529-0B1C2D3E", maria, novo)

    resumos = await _listar(clientes, veiculos, ordens, usuarios, placa=Placa("DEF2G34"))

    assert {r.os.id for r in resumos} == {cenario["em_diagnostico"].id, os_do_novo.id}


async def test_documento_sem_cliente_cadastrado_devolve_lista_vazia(
    clientes, veiculos, ordens, usuarios, cenario
):
    resumos = await _listar(
        clientes, veiculos, ordens, usuarios, documento=Documento.de_texto("12345678909")
    )

    assert resumos == []


async def test_placa_sem_veiculo_cadastrado_devolve_lista_vazia(
    clientes, veiculos, ordens, usuarios, cenario
):
    resumos = await _listar(clientes, veiculos, ordens, usuarios, placa=Placa("XYZ9W99"))

    assert resumos == []


async def test_combina_os_filtros(clientes, veiculos, ordens, usuarios, cenario):
    resumos = await _listar(
        clientes,
        veiculos,
        ordens,
        usuarios,
        documento=Documento.de_texto(CPF_MARIA),
        status=StatusOS.EM_DIAGNOSTICO,
    )

    assert resumos == []


async def test_filtra_pelo_periodo_de_abertura(clientes, veiculos, ordens, usuarios, cenario):
    agora = datetime.now(UTC)

    dentro = await _listar(
        clientes,
        veiculos,
        ordens,
        usuarios,
        abertura_de=agora - timedelta(hours=1),
        abertura_ate=agora + timedelta(hours=1),
    )
    antes = await _listar(
        clientes, veiculos, ordens, usuarios, abertura_ate=agora - timedelta(days=1)
    )

    assert len(dentro) == 2
    assert antes == []


async def test_periodo_sem_fuso_horario_e_recusado_mesmo_sem_cliente_cadastrado(
    clientes, veiculos, ordens, usuarios
):
    with pytest.raises(OrdemServicoInvalida):
        await _listar(
            clientes,
            veiculos,
            ordens,
            usuarios,
            documento=Documento.de_texto("12345678909"),
            abertura_de=datetime(2026, 10, 1),
        )
