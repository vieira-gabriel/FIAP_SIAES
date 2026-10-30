from uuid import uuid4

import pytest

from application.use_cases.atribuir_mecanico import AtribuirMecanico
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.exceptions import (
    AcessoNegado,
    EntidadeNaoEncontrada,
    MecanicoIndisponivel,
    OrdemServicoInvalida,
    TransicaoDeStatusInvalida,
)
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.status_os import StatusOS


async def _usuario(usuarios, perfil: PerfilUsuario, ativo: bool = True) -> Usuario:
    usuario = Usuario(
        nome=perfil.value.title(),
        email=f"{perfil.value.lower()}-{uuid4().hex[:6]}@oficina.com",
        senha_hash="h",
        perfil=perfil,
        ativo=ativo,
    )
    await usuarios.salvar(usuario)
    return usuario


@pytest.fixture
async def os_recebida(ordens) -> OrdemServico:
    os = OrdemServico.abrir(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
    )
    await ordens.salvar(os)
    return os


@pytest.fixture
def atribuir(ordens, usuarios) -> AtribuirMecanico:
    return AtribuirMecanico(ordens, usuarios)


async def test_mecanico_assume_a_os_e_ela_e_salva_em_diagnostico(
    atribuir, ordens, usuarios, os_recebida
):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)

    os = await atribuir.executar(os_recebida.id, mecanico.id, mecanico.id)

    salva = await ordens.buscar_por_id(os_recebida.id)
    assert os is salva
    assert salva.status is StatusOS.EM_DIAGNOSTICO
    assert salva.mecanico_id == mecanico.id
    assert salva.historico[-1].usuario_id == mecanico.id


async def test_gerente_atribui_a_os_a_um_mecanico_e_o_historico_grava_o_gerente(
    atribuir, ordens, usuarios, os_recebida
):
    gerente = await _usuario(usuarios, PerfilUsuario.GERENTE)
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)

    await atribuir.executar(os_recebida.id, mecanico.id, gerente.id)

    salva = await ordens.buscar_por_id(os_recebida.id)
    assert salva.mecanico_id == mecanico.id
    assert salva.historico[-1].usuario_id == gerente.id


async def test_os_inexistente_responde_nao_encontrada(atribuir, usuarios):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)

    with pytest.raises(EntidadeNaoEncontrada):
        await atribuir.executar(uuid4(), mecanico.id, mecanico.id)


@pytest.mark.parametrize("quem", ["mecanico", "responsavel"])
async def test_usuario_inexistente_responde_nao_encontrado(
    atribuir, ordens, usuarios, os_recebida, quem
):
    gerente = await _usuario(usuarios, PerfilUsuario.GERENTE)
    mecanico_id, responsavel_id = (
        (uuid4(), gerente.id) if quem == "mecanico" else (gerente.id, uuid4())
    )

    with pytest.raises(EntidadeNaoEncontrada):
        await atribuir.executar(os_recebida.id, mecanico_id, responsavel_id)

    assert (await ordens.buscar_por_id(os_recebida.id)).status is StatusOS.RECEBIDA


async def test_sem_mecanico_informado_e_recusado(atribuir, ordens, usuarios, os_recebida):
    gerente = await _usuario(usuarios, PerfilUsuario.GERENTE)

    with pytest.raises(OrdemServicoInvalida):
        await atribuir.executar(os_recebida.id, None, gerente.id)

    assert (await ordens.buscar_por_id(os_recebida.id)).status is StatusOS.RECEBIDA


async def test_mecanico_nao_atribui_a_os_a_outro_mecanico(
    atribuir, ordens, usuarios, os_recebida
):
    quem_pede = await _usuario(usuarios, PerfilUsuario.MECANICO)
    outro = await _usuario(usuarios, PerfilUsuario.MECANICO)

    with pytest.raises(AcessoNegado):
        await atribuir.executar(os_recebida.id, outro.id, quem_pede.id)

    assert (await ordens.buscar_por_id(os_recebida.id)).mecanico_id is None


async def test_indicado_que_nao_e_mecanico_ativo_e_recusado(
    atribuir, ordens, usuarios, os_recebida
):
    gerente = await _usuario(usuarios, PerfilUsuario.GERENTE)
    desativado = await _usuario(usuarios, PerfilUsuario.MECANICO, ativo=False)

    with pytest.raises(MecanicoIndisponivel):
        await atribuir.executar(os_recebida.id, desativado.id, gerente.id)

    assert (await ordens.buscar_por_id(os_recebida.id)).mecanico_id is None


async def test_os_que_ja_saiu_de_recebida_nao_muda(atribuir, ordens, usuarios, os_recebida):
    primeiro = await _usuario(usuarios, PerfilUsuario.MECANICO)
    segundo = await _usuario(usuarios, PerfilUsuario.MECANICO)
    await atribuir.executar(os_recebida.id, primeiro.id, primeiro.id)

    with pytest.raises(TransicaoDeStatusInvalida):
        await atribuir.executar(os_recebida.id, segundo.id, segundo.id)

    salva = await ordens.buscar_por_id(os_recebida.id)
    assert salva.mecanico_id == primeiro.id
    assert len(salva.historico) == 2
