from uuid import uuid4

import pytest

from domain.entities.usuario import Usuario
from domain.exceptions import EmailJaCadastrado, EntidadeNaoEncontrada
from domain.repositories.usuario_repository import UsuarioRepository
from domain.value_objects.perfil_usuario import PerfilUsuario


def _usuario(nome="Ana", email="ana@oficina.com"):
    return Usuario(nome=nome, email=email, senha_hash="h", perfil=PerfilUsuario.ATENDENTE)


def test_porta_define_salvar_buscas_e_listagem():
    assert UsuarioRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_email",
        "listar",
    }


async def test_buscar_existente_por_id_encontra_usuario_desativado(usuarios):
    usuario = _usuario()
    usuario.desativar()
    await usuarios.salvar(usuario)

    assert await usuarios.buscar_existente_por_id(usuario.id) == usuario


async def test_buscar_existente_por_id_inexistente(usuarios):
    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await usuarios.buscar_existente_por_id(uuid4())

    assert erro.value.entidade == "Usuário"


async def test_email_de_outro_usuario_nao_esta_livre(usuarios):
    await usuarios.salvar(_usuario())

    with pytest.raises(EmailJaCadastrado):
        await usuarios.garantir_email_livre(_usuario(nome="Outra Ana"))


async def test_o_proprio_email_continua_livre_para_o_dono(usuarios):
    usuario = _usuario()
    await usuarios.salvar(usuario)

    await usuarios.garantir_email_livre(usuario)
