import pytest

from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher


@pytest.fixture
def hasher():
    # Custo mínimo para o teste ficar rápido; a aplicação usa o padrão (12).
    return BcryptPasswordHasher(rounds=4)


async def test_hash_nao_guarda_a_senha_em_texto(hasher):
    senha_hash = await hasher.gerar_hash("senha-secreta")

    assert "senha-secreta" not in senha_hash
    assert senha_hash.startswith("$2b$")


async def test_verifica_senha_correta_e_incorreta(hasher):
    senha_hash = await hasher.gerar_hash("senha-secreta")

    assert await hasher.verificar("senha-secreta", senha_hash)
    assert not await hasher.verificar("outra-senha", senha_hash)


async def test_hashes_da_mesma_senha_sao_diferentes(hasher):
    assert await hasher.gerar_hash("igual") != await hasher.gerar_hash("igual")


async def test_senha_acima_de_72_bytes(hasher):
    senha_hash = await hasher.gerar_hash("a" * 72)

    with pytest.raises(ValueError):
        await hasher.gerar_hash("a" * 73)
    assert not await hasher.verificar("a" * 73, senha_hash)


async def test_hash_em_formato_invalido_nao_verifica(hasher):
    assert not await hasher.verificar("senha", "nao-e-um-hash-bcrypt")
