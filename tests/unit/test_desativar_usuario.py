from uuid import uuid4

import pytest

from application.use_cases.desativar_usuario import DesativarUsuario
from domain.entities.usuario import Usuario
from domain.exceptions import AlteracaoDoProprioAcesso
from domain.value_objects.perfil_usuario import PerfilUsuario


def _usuario(perfil=PerfilUsuario.ATENDENTE):
    return Usuario(nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=perfil)


async def test_desativa_o_usuario_mantendo_o_registro(usuarios):
    ana = _usuario()
    await usuarios.salvar(ana)

    await DesativarUsuario(usuarios).executar(ana.id, responsavel_id=uuid4())

    salvo = await usuarios.buscar_por_id(ana.id)
    assert not salvo.ativo
    assert not salvo.pode_autenticar()


async def test_gerente_nao_desativa_a_si_mesmo(usuarios):
    gerente = _usuario(perfil=PerfilUsuario.GERENTE)
    await usuarios.salvar(gerente)

    with pytest.raises(AlteracaoDoProprioAcesso):
        await DesativarUsuario(usuarios).executar(gerente.id, responsavel_id=gerente.id)

    assert (await usuarios.buscar_por_id(gerente.id)).ativo
