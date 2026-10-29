import pytest

from application.use_cases.cadastrar_usuario import CadastrarUsuario
from domain.exceptions import EmailJaCadastrado, UsuarioInvalido
from domain.value_objects.perfil_usuario import PerfilUsuario


async def test_cadastra_usuario_guardando_so_o_hash_da_senha(usuarios, password_hasher):
    usuario = await CadastrarUsuario(usuarios, password_hasher).executar(
        "Ana", "Ana@Oficina.com", "senha-forte", PerfilUsuario.MECANICO
    )

    salvo = await usuarios.buscar_por_id(usuario.id)
    assert salvo.email == "ana@oficina.com"
    assert salvo.perfil is PerfilUsuario.MECANICO
    assert salvo.senha_hash == "hash:senha-forte"
    assert salvo.ativo


async def test_recusa_email_ja_cadastrado(usuarios, password_hasher):
    cadastrar = CadastrarUsuario(usuarios, password_hasher)
    await cadastrar.executar("Ana", "ana@oficina.com", "senha-forte", PerfilUsuario.ATENDENTE)

    with pytest.raises(EmailJaCadastrado):
        await cadastrar.executar("Outra", " ANA@oficina.com ", "senha-forte", PerfilUsuario.GERENTE)

    assert len(usuarios.dados) == 1


async def test_dados_invalidos_nao_gravam_nada(usuarios, password_hasher):
    with pytest.raises(UsuarioInvalido):
        await CadastrarUsuario(usuarios, password_hasher).executar(
            "", "ana@oficina.com", "senha-forte", PerfilUsuario.ATENDENTE
        )

    assert usuarios.dados == {}
