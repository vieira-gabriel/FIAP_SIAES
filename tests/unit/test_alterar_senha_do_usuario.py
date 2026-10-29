from uuid import uuid4

import pytest

from application.use_cases.alterar_senha_do_usuario import AlterarSenhaDoUsuario
from domain.entities.usuario import Usuario
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.perfil_usuario import PerfilUsuario


async def test_grava_so_o_hash_da_nova_senha(usuarios, password_hasher):
    ana = Usuario(
        nome="Ana", email="ana@oficina.com", senha_hash="hash:antiga", perfil=PerfilUsuario.MECANICO
    )
    await usuarios.salvar(ana)

    await AlterarSenhaDoUsuario(usuarios, password_hasher).executar(ana.id, "nova-senha")

    assert (await usuarios.buscar_por_id(ana.id)).senha_hash == "hash:nova-senha"


async def test_usuario_inexistente(usuarios, password_hasher):
    with pytest.raises(EntidadeNaoEncontrada):
        await AlterarSenhaDoUsuario(usuarios, password_hasher).executar(uuid4(), "nova-senha")
