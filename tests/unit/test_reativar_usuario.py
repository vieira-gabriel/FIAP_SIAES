from application.use_cases.reativar_usuario import ReativarUsuario
from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario


async def test_reativa_usuario_desativado(usuarios):
    ana = Usuario(
        nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=PerfilUsuario.MECANICO
    )
    ana.desativar()
    await usuarios.salvar(ana)

    await ReativarUsuario(usuarios).executar(ana.id)

    assert (await usuarios.buscar_por_id(ana.id)).pode_autenticar()
