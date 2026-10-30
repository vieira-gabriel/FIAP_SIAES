"""Despacho dos eventos de domínio na mesma transação da operação, com PostgreSQL real
(RNF-08; issue #89)."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from application.events.event_dispatcher import EventHandler
from domain.entities.usuario import Usuario
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

PECA = {
    "codigo_referencia": "FLT-001",
    "nome": "Filtro de óleo",
    "preco_unitario": "35.90",
    "prazo_reposicao_dias": 3,
}


class GravadorDeTeste(EventHandler):
    """Handler de teste: grava uma linha na mesma sessão da operação, ou falha de propósito."""

    def __init__(self, sessao, tabela: str, falhar: bool):
        self._sessao = sessao
        self._tabela = tabela
        self._falhar = falhar

    async def tratar(self, evento):
        if self._falhar:
            raise RuntimeError("falha simulada no handler")
        await self._sessao.execute(
            text(f"INSERT INTO {self._tabela} (evento_id) VALUES (:id)"),
            {"id": str(evento.event_id)},
        )
        return []


@pytest.fixture
def gerente():
    usuario = Usuario(
        nome="Gerente", email="g@oficina.com", senha_hash="h", perfil=PerfilUsuario.GERENTE
    )
    return {"Authorization": f"Bearer {app.state.token_service.emitir(usuario)}"}


@pytest.fixture
async def tabela_do_handler(conexao):
    nome = f"teste_despacho_{uuid4().hex}"
    await conexao.execute(text(f"CREATE TABLE {nome} (evento_id text PRIMARY KEY)"))
    return nome


async def _peca_com_estoque_zerado(cliente_http, gerente) -> str:
    resposta = await cliente_http.post(
        "/pecas", json=PECA | {"quantidade_fisica_inicial": 0}, headers=gerente
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


async def _quantidade_fisica(conexao, peca_id: str) -> int:
    return await conexao.scalar(
        text("SELECT quantidade_fisica FROM estoque_pecas WHERE peca_id = :id"), {"id": peca_id}
    )


async def test_handler_que_grava_e_confirmado_junto_com_a_operacao(
    cliente_http, gerente, conexao, tabela_do_handler, monkeypatch
):
    peca_id = await _peca_com_estoque_zerado(cliente_http, gerente)
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            (
                SaldoPecaAtualizadoEvent,
                lambda sessao: GravadorDeTeste(sessao, tabela_do_handler, False),
            )
        ],
    )

    resposta = await cliente_http.post(
        f"/pecas/{peca_id}/reposicao", json={"quantidade": 5}, headers=gerente
    )

    assert resposta.status_code in (200, 201)
    assert await _quantidade_fisica(conexao, peca_id) == 5
    gravados = await conexao.scalar(text(f"SELECT count(*) FROM {tabela_do_handler}"))
    assert gravados == 1


async def test_falha_do_handler_desfaz_a_operacao_inteira(
    cliente_http, gerente, conexao, tabela_do_handler, monkeypatch
):
    peca_id = await _peca_com_estoque_zerado(cliente_http, gerente)
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            (
                SaldoPecaAtualizadoEvent,
                lambda sessao: GravadorDeTeste(sessao, tabela_do_handler, True),
            )
        ],
    )

    # O transporte de teste repassa a exceção depois da resposta 500 do tratador global (o
    # servidor real só a registra no log); o que importa aqui é o estado do banco.
    with pytest.raises(RuntimeError, match="falha simulada no handler"):
        await cliente_http.post(
            f"/pecas/{peca_id}/reposicao", json={"quantidade": 5}, headers=gerente
        )

    assert await _quantidade_fisica(conexao, peca_id) == 0
    gravados = await conexao.scalar(text(f"SELECT count(*) FROM {tabela_do_handler}"))
    assert gravados == 0
