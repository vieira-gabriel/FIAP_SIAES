import asyncio

import pytest
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.verificador_do_banco import VerificadorDoBancoSqlAlchemy


class ConexaoFalsa:
    def __init__(self, falha: Exception | None = None, demora_segundos: float = 0):
        self._falha = falha
        self._demora_segundos = demora_segundos
        self.consultas: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excecao):
        return None

    async def execute(self, consulta):
        await asyncio.sleep(self._demora_segundos)
        if self._falha is not None:
            raise self._falha
        self.consultas.append(str(consulta))


class EngineFalsa:
    def __init__(self, conexao: ConexaoFalsa):
        self._conexao = conexao

    def connect(self):
        return self._conexao


async def test_banco_que_responde_esta_disponivel():
    conexao = ConexaoFalsa()

    disponivel = await VerificadorDoBancoSqlAlchemy(EngineFalsa(conexao)).esta_disponivel()

    assert disponivel is True
    assert conexao.consultas == ["SELECT 1"]


@pytest.mark.parametrize(
    "falha",
    [ConnectionRefusedError("conexão recusada"), SQLAlchemyError("credencial inválida")],
)
async def test_falha_de_conexao_ou_do_banco_deixa_de_estar_disponivel(falha):
    engine = EngineFalsa(ConexaoFalsa(falha=falha))

    assert await VerificadorDoBancoSqlAlchemy(engine).esta_disponivel() is False


async def test_banco_que_demora_mais_que_o_tempo_limite_nao_esta_disponivel():
    engine = EngineFalsa(ConexaoFalsa(demora_segundos=1))
    verificador = VerificadorDoBancoSqlAlchemy(engine, tempo_limite_segundos=0.05)

    assert await verificador.esta_disponivel() is False


async def test_erro_inesperado_nao_e_escondido():
    engine = EngineFalsa(ConexaoFalsa(falha=ValueError("defeito no código")))

    with pytest.raises(ValueError):
        await VerificadorDoBancoSqlAlchemy(engine).esta_disponivel()
