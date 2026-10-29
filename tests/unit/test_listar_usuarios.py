from application.use_cases.listar_usuarios import ListarUsuarios
from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario


async def test_lista_ativos_e_desativados_em_ordem_de_nome(usuarios):
    bia = Usuario(nome="Bia", email="bia@oficina.com", senha_hash="h", perfil=PerfilUsuario.GERENTE)
    ana = Usuario(
        nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=PerfilUsuario.MECANICO
    )
    ana.desativar()
    await usuarios.salvar(bia)
    await usuarios.salvar(ana)

    assert await ListarUsuarios(usuarios).executar() == [ana, bia]
