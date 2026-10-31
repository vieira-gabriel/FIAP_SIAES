import pytest

from application.ports.token_service import TokenService, UsuarioAutenticado
from application.use_cases.autenticar_usuario import AutenticarUsuario
from domain.entities.usuario import Usuario
from domain.exceptions import CredenciaisInvalidas
from domain.value_objects.perfil_usuario import PerfilUsuario


class TokenServiceFalso(TokenService):
    def emitir(self, usuario):
        return f"token:{usuario.id}:{usuario.perfil.value}"

    def validar(self, token):
        _, usuario_id, perfil = token.split(":")
        return UsuarioAutenticado(usuario_id, PerfilUsuario(perfil))


@pytest.fixture
async def usuarios(usuarios, password_hasher):
    await usuarios.salvar(
        Usuario(
            nome="Gerente",
            email="admin@oficina.com",
            senha_hash=await password_hasher.gerar_hash("senha-correta"),
            perfil=PerfilUsuario.GERENTE,
        )
    )
    return usuarios


@pytest.fixture
def autenticar(usuarios, password_hasher):
    return AutenticarUsuario(usuarios, password_hasher, TokenServiceFalso())


async def test_login_valido_devolve_token_com_perfil(autenticar, usuarios):
    gerente = await usuarios.buscar_por_email("admin@oficina.com")

    token = await autenticar.executar("admin@oficina.com", "senha-correta")

    assert token == f"token:{gerente.id}:GERENTE"


async def test_email_e_comparado_sem_diferenciar_maiusculas_e_espacos(autenticar):
    assert await autenticar.executar("  Admin@Oficina.com ", "senha-correta")


async def test_senha_incorreta(autenticar):
    with pytest.raises(CredenciaisInvalidas):
        await autenticar.executar("admin@oficina.com", "senha-errada")


async def test_email_inexistente(autenticar):
    with pytest.raises(CredenciaisInvalidas):
        await autenticar.executar("ninguem@oficina.com", "senha-correta")


async def test_usuario_desativado_nao_faz_login(autenticar, usuarios):
    (await usuarios.buscar_por_email("admin@oficina.com")).desativar()

    with pytest.raises(CredenciaisInvalidas):
        await autenticar.executar("admin@oficina.com", "senha-correta")


async def test_mensagem_nao_revela_se_o_email_existe(autenticar):
    with pytest.raises(CredenciaisInvalidas) as email_inexistente:
        await autenticar.executar("ninguem@oficina.com", "x")
    with pytest.raises(CredenciaisInvalidas) as senha_errada:
        await autenticar.executar("admin@oficina.com", "x")

    assert str(email_inexistente.value) == str(senha_errada.value)
