from uuid import uuid4

import pytest

from application.use_cases.atualizar_usuario import AtualizarUsuario
from domain.entities.usuario import Usuario
from domain.exceptions import AlteracaoDoProprioAcesso, EmailJaCadastrado, EntidadeNaoEncontrada
from domain.value_objects.perfil_usuario import PerfilUsuario

GERENTE_ID = uuid4()


def _usuario(nome="Ana", email="ana@oficina.com", perfil=PerfilUsuario.ATENDENTE):
    return Usuario(nome=nome, email=email, senha_hash="hash:x", perfil=perfil)


async def test_atualiza_nome_email_e_perfil_sem_mexer_na_senha(usuarios):
    ana = _usuario()
    await usuarios.salvar(ana)

    await AtualizarUsuario(usuarios).executar(
        ana.id, "Ana Souza", "ana.souza@oficina.com", PerfilUsuario.MECANICO, GERENTE_ID
    )

    salvo = await usuarios.buscar_por_id(ana.id)
    assert (salvo.nome, salvo.email, salvo.perfil) == (
        "Ana Souza",
        "ana.souza@oficina.com",
        PerfilUsuario.MECANICO,
    )
    assert salvo.senha_hash == "hash:x"


async def test_recusa_email_de_outro_usuario(usuarios):
    ana, bia = _usuario(), _usuario(nome="Bia", email="bia@oficina.com")
    await usuarios.salvar(ana)
    await usuarios.salvar(bia)

    with pytest.raises(EmailJaCadastrado):
        await AtualizarUsuario(usuarios).executar(
            bia.id, "Bia", "ana@oficina.com", PerfilUsuario.ATENDENTE, GERENTE_ID
        )


async def test_gerente_nao_muda_o_proprio_perfil(usuarios):
    gerente = _usuario(perfil=PerfilUsuario.GERENTE)
    await usuarios.salvar(gerente)

    with pytest.raises(AlteracaoDoProprioAcesso):
        await AtualizarUsuario(usuarios).executar(
            gerente.id, "Ana", "ana@oficina.com", PerfilUsuario.ATENDENTE, gerente.id
        )

    assert (await usuarios.buscar_por_id(gerente.id)).perfil is PerfilUsuario.GERENTE


async def test_gerente_atualiza_os_proprios_dados_mantendo_o_perfil(usuarios):
    gerente = _usuario(perfil=PerfilUsuario.GERENTE)
    await usuarios.salvar(gerente)

    atualizado = await AtualizarUsuario(usuarios).executar(
        gerente.id, "Ana Gerente", "ana@oficina.com", PerfilUsuario.GERENTE, gerente.id
    )

    assert atualizado.nome == "Ana Gerente"


async def test_usuario_inexistente(usuarios):
    with pytest.raises(EntidadeNaoEncontrada):
        await AtualizarUsuario(usuarios).executar(
            uuid4(), "Ana", "ana@oficina.com", PerfilUsuario.ATENDENTE, GERENTE_ID
        )
