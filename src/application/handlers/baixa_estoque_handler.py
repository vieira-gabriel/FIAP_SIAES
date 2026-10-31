from application.events.event_dispatcher import EventHandler
from domain.events.domain_event import DomainEvent
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.exceptions import EntidadeNaoEncontrada
from domain.repositories.estoque_repository import EstoqueRepository


class BaixaEstoqueHandler(EventHandler[ExecucaoIniciadaEvent]):
    """Dá a baixa definitiva nas peças reservadas da OS que iniciou a execução (RF-20).

    Reduz a quantidade física e a reservada de cada peça, sem alterar o saldo disponível. Roda na
    transação do início da execução, com a OS já bloqueada, e bloqueia o estoque de cada peça em
    ordem de id (RNF-08, RNF-09). Peça baixada não volta ao estoque no cancelamento (RF-18).
    """

    def __init__(self, estoques: EstoqueRepository):
        self._estoques = estoques

    async def tratar(self, evento: ExecucaoIniciadaEvent) -> list[DomainEvent]:
        for baixa in sorted(evento.baixas, key=lambda baixa: baixa.peca_id):
            estoque = await self._estoques.buscar_por_peca(baixa.peca_id)
            if estoque is None:
                raise EntidadeNaoEncontrada("Estoque da peça", baixa.peca_id)
            estoque.baixar(baixa.quantidade)
            await self._estoques.salvar(estoque)
        return []
