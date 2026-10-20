import pytest

from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher


@pytest.fixture
def hasher():
    # Custo mínimo para o teste ficar rápido; a aplicação usa o padrão (12).
    return BcryptPasswordHasher(rounds=4)


def test_hash_nao_guarda_a_senha_em_texto(hasher):
    senha_hash = hasher.gerar_hash("senha-secreta")

    assert "senha-secreta" not in senha_hash
    assert senha_hash.startswith("$2b$")


def test_verifica_senha_correta_e_incorreta(hasher):
    senha_hash = hasher.gerar_hash("senha-secreta")

    assert hasher.verificar("senha-secreta", senha_hash)
    assert not hasher.verificar("outra-senha", senha_hash)


def test_hashes_da_mesma_senha_sao_diferentes(hasher):
    assert hasher.gerar_hash("igual") != hasher.gerar_hash("igual")


def test_senha_acima_de_72_bytes(hasher):
    senha_hash = hasher.gerar_hash("a" * 72)

    with pytest.raises(ValueError):
        hasher.gerar_hash("a" * 73)
    assert not hasher.verificar("a" * 73, senha_hash)


def test_hash_em_formato_invalido_nao_verifica(hasher):
    assert not hasher.verificar("senha", "nao-e-um-hash-bcrypt")
