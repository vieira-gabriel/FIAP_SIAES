import pytest

from domain.entities.usuario import Usuario
from domain.exceptions import UsuarioInvalido
from domain.value_objects.perfil_usuario import PerfilUsuario


def criar_usuario(**alteracoes) -> Usuario:
    dados = {
        "nome": "Ana Atendente",
        "email": "ana@oficina.com",
        "senha_hash": "hash",
        "perfil": PerfilUsuario.ATENDENTE,
    }
    dados.update(alteracoes)
    return Usuario(**dados)


def test_cria_usuario_ativo_com_id():
    usuario = criar_usuario()

    assert usuario.ativo
    assert usuario.id is not None
    assert usuario.pode_autenticar()


def test_normaliza_email_e_nome():
    usuario = criar_usuario(nome="  Ana  ", email="  Ana@Oficina.COM ")

    assert usuario.nome == "Ana"
    assert usuario.email == "ana@oficina.com"


@pytest.mark.parametrize(
    "alteracao",
    [
        {"nome": "   "},
        {"email": "sem-arroba"},
        {"email": ""},
        {"senha_hash": ""},
        {"perfil": "GERENTE"},
    ],
)
def test_rejeita_dados_invalidos(alteracao):
    with pytest.raises(UsuarioInvalido):
        criar_usuario(**alteracao)


def test_usuario_desativado_nao_autentica_e_pode_ser_reativado():
    usuario = criar_usuario()

    usuario.desativar()
    assert not usuario.pode_autenticar()

    usuario.reativar()
    assert usuario.pode_autenticar()


def test_alterar_senha_hash():
    usuario = criar_usuario()

    usuario.alterar_senha_hash("novo-hash")

    assert usuario.senha_hash == "novo-hash"
    with pytest.raises(UsuarioInvalido):
        usuario.alterar_senha_hash("")


def test_igualdade_pela_identidade():
    usuario = criar_usuario()
    outro_com_mesmos_dados = criar_usuario()

    assert usuario != outro_com_mesmos_dados
    assert usuario == criar_usuario(id=usuario.id, nome="Outro nome")
    assert len({usuario, outro_com_mesmos_dados}) == 2
