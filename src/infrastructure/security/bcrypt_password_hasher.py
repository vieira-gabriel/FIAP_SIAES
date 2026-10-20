import asyncio

import bcrypt

from application.ports.password_hasher import PasswordHasher

# O bcrypt considera no máximo 72 bytes da senha; a partir da versão 5 ele recusa
# senhas maiores em vez de truncá-las silenciosamente.
_LIMITE_BYTES_BCRYPT = 72


class BcryptPasswordHasher(PasswordHasher):
    """O bcrypt roda em uma thread separada para não bloquear o loop de eventos."""

    def __init__(self, rounds: int = 12):
        self._rounds = rounds

    async def gerar_hash(self, senha: str) -> str:
        return await asyncio.to_thread(self._gerar_hash, senha)

    async def verificar(self, senha: str, senha_hash: str) -> bool:
        return await asyncio.to_thread(self._verificar, senha, senha_hash)

    def _gerar_hash(self, senha: str) -> str:
        senha_bytes = senha.encode("utf-8")
        if len(senha_bytes) > _LIMITE_BYTES_BCRYPT:
            raise ValueError(f"A senha não pode ter mais de {_LIMITE_BYTES_BCRYPT} bytes.")
        return bcrypt.hashpw(senha_bytes, bcrypt.gensalt(rounds=self._rounds)).decode("utf-8")

    def _verificar(self, senha: str, senha_hash: str) -> bool:
        senha_bytes = senha.encode("utf-8")
        if len(senha_bytes) > _LIMITE_BYTES_BCRYPT:
            return False
        try:
            return bcrypt.checkpw(senha_bytes, senha_hash.encode("utf-8"))
        except ValueError:
            # Hash armazenado em formato inválido.
            return False
