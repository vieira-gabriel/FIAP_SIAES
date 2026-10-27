from dataclasses import dataclass

import pytest

from application.events.event_dispatcher import EventDispatcher, EventHandler
from domain.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class EventoA(DomainEvent):
    nome: str = "A"


@dataclass(frozen=True, kw_only=True)
class EventoB(DomainEvent):
    nome: str = "B"


class HandlerRegistrador(EventHandler):
    """Anota cada evento recebido e devolve os eventos configurados para a reação."""

    def __init__(self, registro: list[str], identificacao: str, gera=()):
        self._registro = registro
        self._identificacao = identificacao
        self._gera = list(gera)

    async def tratar(self, evento):
        self._registro.append(f"{self._identificacao}:{evento.nome}")
        eventos_gerados, self._gera = self._gera, []
        return eventos_gerados


class HandlerComFalha(EventHandler):
    async def tratar(self, evento):
        raise RuntimeError("saldo insuficiente")


@pytest.fixture
def dispatcher():
    return EventDispatcher()


@pytest.fixture
def registro():
    return []


async def test_handler_registrado_recebe_o_evento(dispatcher, registro):
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "h1"))

    await dispatcher.despachar([EventoA()])

    assert registro == ["h1:A"]


async def test_varios_handlers_sao_chamados_na_ordem_de_registro(dispatcher, registro):
    for identificacao in ("h1", "h2", "h3"):
        dispatcher.registrar(EventoA, HandlerRegistrador(registro, identificacao))

    await dispatcher.despachar([EventoA()])

    assert registro == ["h1:A", "h2:A", "h3:A"]


async def test_handler_recebe_apenas_o_tipo_de_evento_registrado(dispatcher, registro):
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "so_a"))
    dispatcher.registrar(EventoB, HandlerRegistrador(registro, "so_b"))

    await dispatcher.despachar([EventoB()])

    assert registro == ["so_b:B"]


async def test_evento_sem_handler_e_ignorado(dispatcher):
    await dispatcher.despachar([EventoA()])


async def test_lista_vazia_nao_chama_handlers(dispatcher, registro):
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "h1"))

    await dispatcher.despachar([])

    assert registro == []


async def test_eventos_gerados_pelos_handlers_tambem_sao_despachados(dispatcher, registro):
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "estorno", gera=[EventoB()]))
    dispatcher.registrar(EventoB, HandlerRegistrador(registro, "alocacao"))

    await dispatcher.despachar([EventoA()])

    assert registro == ["estorno:A", "alocacao:B"]


async def test_eventos_gerados_entram_depois_dos_que_ja_estavam_na_fila(dispatcher, registro):
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "h_a", gera=[EventoB(nome="B2")]))
    dispatcher.registrar(EventoB, HandlerRegistrador(registro, "h_b"))

    await dispatcher.despachar([EventoA(), EventoB(nome="B1")])

    assert registro == ["h_a:A", "h_b:B1", "h_b:B2"]


async def test_despacha_em_cadeia_ate_nao_restar_evento(dispatcher, registro):
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "h_a", gera=[EventoB()]))
    dispatcher.registrar(EventoB, HandlerRegistrador(registro, "h_b", gera=[EventoA(nome="A2")]))

    await dispatcher.despachar([EventoA()])

    assert registro == ["h_a:A", "h_b:B", "h_a:A2"]


async def test_falha_em_handler_propaga_e_interrompe_o_despacho(dispatcher, registro):
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "antes"))
    dispatcher.registrar(EventoA, HandlerComFalha())
    dispatcher.registrar(EventoA, HandlerRegistrador(registro, "depois"))
    dispatcher.registrar(EventoB, HandlerRegistrador(registro, "proximo_evento"))

    with pytest.raises(RuntimeError, match="saldo insuficiente"):
        await dispatcher.despachar([EventoA(), EventoB()])

    assert registro == ["antes:A"]


def test_event_handler_exige_implementar_tratar():
    with pytest.raises(TypeError):
        EventHandler()
