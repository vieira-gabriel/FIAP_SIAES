import pytest

from application.ports.password_hasher import PasswordHasher
from application.use_cases.criar_carga_inicial import CriarCargaInicial, SenhasDaCargaInicial
from domain.repositories.usuario_repository import UsuarioRepository
from domain.value_objects.perfil_usuario import PerfilUsuario


class UsuarioRepositoryEmMemoria(UsuarioRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, usuario):
        self.dados[usuario.id] = usuario

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_email(self, email):
        return next((u for u in self.dados.values() if u.email == email), None)


class PasswordHasherFalso(PasswordHasher):
    async def gerar_hash(self, senha):
        return f"hash:{senha}"

    async def verificar(self, senha, senha_hash):
        return senha_hash == f"hash:{senha}"


@pytest.fixture
def usuarios():
    return UsuarioRepositoryEmMemoria()


@pytest.fixture
def carga_inicial(usuarios):
    return CriarCargaInicial(usuarios, PasswordHasherFalso())


def _perfis_por_email(usuarios):
    return {u.email: u.perfil for u in usuarios.dados.values()}


async def test_sem_senhas_de_demonstracao_cria_apenas_o_gerente_padrao(carga_inicial, usuarios):
    await carga_inicial.executar(SenhasDaCargaInicial(gerente="senha-admin"))

    gerente = await usuarios.buscar_por_email("admin@oficina.com")
    assert _perfis_por_email(usuarios) == {"admin@oficina.com": PerfilUsuario.GERENTE}
    assert gerente.senha_hash == "hash:senha-admin"
    assert gerente.ativo


async def test_com_senhas_de_demonstracao_cria_atendente_e_mecanico(carga_inicial, usuarios):
    await carga_inicial.executar(
        SenhasDaCargaInicial(gerente="senha-admin", atendente="senha-at", mecanico="senha-mec")
    )

    assert _perfis_por_email(usuarios) == {
        "admin@oficina.com": PerfilUsuario.GERENTE,
        "atendente@oficina.com": PerfilUsuario.ATENDENTE,
        "mecanico@oficina.com": PerfilUsuario.MECANICO,
    }
    mecanico = await usuarios.buscar_por_email("mecanico@oficina.com")
    assert mecanico.senha_hash == "hash:senha-mec"


async def test_executar_de_novo_nao_duplica_usuarios(carga_inicial, usuarios):
    senhas = SenhasDaCargaInicial(gerente="senha-admin", atendente="senha-at", mecanico="senha-mec")

    await carga_inicial.executar(senhas)
    await carga_inicial.executar(senhas)

    assert len(usuarios.dados) == 3


async def test_usuario_existente_mantem_senha_e_situacao(carga_inicial, usuarios):
    await carga_inicial.executar(SenhasDaCargaInicial(gerente="senha-original"))
    gerente = await usuarios.buscar_por_email("admin@oficina.com")
    gerente.alterar_senha_hash("hash:senha-trocada-pelo-gerente")
    gerente.desativar()

    await carga_inicial.executar(SenhasDaCargaInicial(gerente="senha-original"))

    gerente = await usuarios.buscar_por_email("admin@oficina.com")
    assert gerente.senha_hash == "hash:senha-trocada-pelo-gerente"
    assert not gerente.ativo


def test_senhas_nao_aparecem_na_representacao():
    texto = repr(SenhasDaCargaInicial(gerente="segredo-1", atendente="segredo-2", mecanico="x3"))

    assert "segredo" not in texto
    assert "x3" not in texto
