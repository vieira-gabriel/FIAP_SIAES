import pytest
from sqlalchemy.exc import IntegrityError

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.database.engine import criar_fabrica_de_sessoes
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository


@pytest.fixture
def fabrica_de_sessoes(banco_migrado):
    return criar_fabrica_de_sessoes(banco_migrado)


async def _salvar(fabrica_de_sessoes, usuario):
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        await PostgresUsuarioRepository(unidade.sessao).salvar(usuario)


async def _buscar_por_email(fabrica_de_sessoes, email):
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        return await PostgresUsuarioRepository(unidade.sessao).buscar_por_email(email)


def _mecanico(email="mecanico@oficina.com"):
    return Usuario(
        nome="Mecânico",
        email=email,
        senha_hash="$2b$12$hash",
        perfil=PerfilUsuario.MECANICO,
    )


async def test_usuario_salvo_e_encontrado_por_email_e_por_id(fabrica_de_sessoes):
    mecanico = _mecanico()
    await _salvar(fabrica_de_sessoes, mecanico)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        repositorio = PostgresUsuarioRepository(unidade.sessao)
        por_email = await repositorio.buscar_por_email("mecanico@oficina.com")
        por_id = await repositorio.buscar_por_id(mecanico.id)

    for encontrado in (por_email, por_id):
        assert encontrado == mecanico
        assert encontrado.nome == "Mecânico"
        assert encontrado.senha_hash == "$2b$12$hash"
        assert encontrado.perfil is PerfilUsuario.MECANICO
        assert encontrado.ativo


async def test_busca_de_usuario_inexistente_devolve_none(fabrica_de_sessoes):
    assert await _buscar_por_email(fabrica_de_sessoes, "ninguem@oficina.com") is None


async def test_salvar_de_novo_atualiza_o_usuario(fabrica_de_sessoes):
    mecanico = _mecanico()
    await _salvar(fabrica_de_sessoes, mecanico)

    mecanico.desativar()
    mecanico.alterar_senha_hash("$2b$12$outro")
    await _salvar(fabrica_de_sessoes, mecanico)

    atualizado = await _buscar_por_email(fabrica_de_sessoes, "mecanico@oficina.com")
    assert not atualizado.ativo
    assert atualizado.senha_hash == "$2b$12$outro"


async def test_email_repetido_e_recusado_pelo_banco(fabrica_de_sessoes):
    await _salvar(fabrica_de_sessoes, _mecanico())

    with pytest.raises(IntegrityError):
        await _salvar(fabrica_de_sessoes, _mecanico())
