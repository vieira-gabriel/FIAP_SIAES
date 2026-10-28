from uuid import uuid4

import pytest

from application.use_cases.detalhar_usuario import DetalharUsuario
from domain.entities.usuario import Usuario
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.perfil_usuario import PerfilUsuario


async def test_detalha_inclusive_usuario_desativado(usuarios):
    ana = Usuario(
        nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=PerfilUsuario.MECANICO
    )
    ana.desativar()
    await usuarios.salvar(ana)

    assert await DetalharUsuario(usuarios).executar(ana.id) == ana


async def test_usuario_inexistente(usuarios):
    with pytest.raises(EntidadeNaoEncontrada):
        await DetalharUsuario(usuarios).executar(uuid4())
