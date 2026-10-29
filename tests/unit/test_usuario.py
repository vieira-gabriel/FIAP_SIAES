from uuid import uuid4

import pytest

from domain.entities.usuario import Usuario
from domain.exceptions import AlteracaoDoProprioAcesso, UsuarioInvalido
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


def test_atualizar_dados_normaliza_e_valida():
    usuario = criar_usuario()

    usuario.atualizar_dados("  Ana Souza ", " Ana.Souza@Oficina.com ")

    assert (usuario.nome, usuario.email) == ("Ana Souza", "ana.souza@oficina.com")
    with pytest.raises(UsuarioInvalido):
        usuario.atualizar_dados("Ana", "sem-arroba")
    assert usuario.email == "ana.souza@oficina.com"


def test_gerente_altera_o_perfil_de_outro_usuario():
    usuario = criar_usuario()

    usuario.alterar_perfil(PerfilUsuario.MECANICO, responsavel_id=uuid4())

    assert usuario.perfil is PerfilUsuario.MECANICO


def test_ninguem_altera_o_proprio_perfil():
    gerente = criar_usuario(perfil=PerfilUsuario.GERENTE)

    with pytest.raises(AlteracaoDoProprioAcesso):
        gerente.alterar_perfil(PerfilUsuario.ATENDENTE, responsavel_id=gerente.id)

    assert gerente.perfil is PerfilUsuario.GERENTE


def test_manter_o_proprio_perfil_e_permitido():
    gerente = criar_usuario(perfil=PerfilUsuario.GERENTE)

    gerente.alterar_perfil(PerfilUsuario.GERENTE, responsavel_id=gerente.id)

    assert gerente.perfil is PerfilUsuario.GERENTE


def test_alterar_para_perfil_desconhecido_e_recusado():
    with pytest.raises(UsuarioInvalido):
        criar_usuario().alterar_perfil("CHEFE", responsavel_id=uuid4())


def test_desativar_por_outro_usuario():
    usuario = criar_usuario()

    usuario.desativar_por(responsavel_id=uuid4())

    assert not usuario.ativo


def test_ninguem_desativa_o_proprio_acesso():
    gerente = criar_usuario(perfil=PerfilUsuario.GERENTE)

    with pytest.raises(AlteracaoDoProprioAcesso) as erro:
        gerente.desativar_por(responsavel_id=gerente.id)

    assert gerente.ativo
    assert erro.value.acao == "desativar o próprio acesso"
