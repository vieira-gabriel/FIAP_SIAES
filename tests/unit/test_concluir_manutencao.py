from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.use_cases.concluir_manutencao import ConcluirManutencao
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.exceptions import AcessoNegado, EntidadeNaoEncontrada, TransicaoDeStatusInvalida
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.status_os import StatusOS

ANTES = datetime.now(UTC)


@pytest.fixture
def concluir(ordens, usuarios) -> ConcluirManutencao:
    return ConcluirManutencao(ordens, usuarios)


async def _usuario(usuarios, perfil: PerfilUsuario, ativo: bool = True) -> Usuario:
    usuario = Usuario(
        nome=perfil.value.title(),
        email=f"{uuid4().hex[:8]}@oficina.com",
        senha_hash="hash",
        perfil=perfil,
        ativo=ativo,
    )
    await usuarios.salvar(usuario)
    return usuario


async def _os(ordens, mecanico: Usuario, status=StatusOS.EM_EXECUCAO) -> OrdemServico:
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        mecanico_id=mecanico.id,
        status=status,
    )
    await ordens.salvar(os)
    return os


async def test_mecanico_atribuido_conclui_e_a_conclusao_e_salva(concluir, ordens, usuarios):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os = await _os(ordens, mecanico)

    concluida = await concluir.executar(os.id, mecanico.id)

    assert concluida.status is StatusOS.FINALIZADA
    assert concluida.data_finalizacao >= ANTES
    assert (concluida.historico[-1].status_novo, concluida.historico[-1].usuario_id) == (
        StatusOS.FINALIZADA,
        mecanico.id,
    )
    assert (await ordens.buscar_por_id(os.id)).status is StatusOS.FINALIZADA


async def test_gerente_conclui_a_manutencao_de_qualquer_os(concluir, ordens, usuarios):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    gerente = await _usuario(usuarios, PerfilUsuario.GERENTE)
    os = await _os(ordens, mecanico)

    assert (await concluir.executar(os.id, gerente.id)).status is StatusOS.FINALIZADA


async def test_outro_mecanico_nao_conclui(concluir, ordens, usuarios):
    atribuido = await _usuario(usuarios, PerfilUsuario.MECANICO)
    outro = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os = await _os(ordens, atribuido)

    with pytest.raises(AcessoNegado):
        await concluir.executar(os.id, outro.id)

    assert os.status is StatusOS.EM_EXECUCAO


async def test_usuario_desativado_nao_conclui(concluir, ordens, usuarios):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO, ativo=False)
    os = await _os(ordens, mecanico)

    with pytest.raises(AcessoNegado):
        await concluir.executar(os.id, mecanico.id)


@pytest.mark.parametrize("status", [StatusOS.AGUARDANDO_EXECUCAO, StatusOS.FINALIZADA])
async def test_so_conclui_a_partir_de_em_execucao(concluir, ordens, usuarios, status):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os = await _os(ordens, mecanico, status=status)

    with pytest.raises(TransicaoDeStatusInvalida):
        await concluir.executar(os.id, mecanico.id)

    assert os.status is status


async def test_os_inexistente(concluir, usuarios):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)

    with pytest.raises(EntidadeNaoEncontrada):
        await concluir.executar(uuid4(), mecanico.id)


async def test_usuario_inexistente(concluir, ordens, usuarios):
    mecanico = await _usuario(usuarios, PerfilUsuario.MECANICO)
    os = await _os(ordens, mecanico)

    with pytest.raises(EntidadeNaoEncontrada):
        await concluir.executar(os.id, uuid4())
