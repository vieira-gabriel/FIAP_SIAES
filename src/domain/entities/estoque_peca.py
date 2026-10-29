from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from domain.events.domain_event import DomainEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.exceptions import (
    AlocacaoInvalida,
    PecaInvalida,
    QuantidadeFisicaAbaixoDaReservada,
    QuantidadeInvalida,
    SaldoInsuficiente,
)
from domain.value_objects.alocacao_peca import AlocacaoPeca
from domain.value_objects.pendencia_peca import PendenciaPeca


@dataclass(eq=False)
class EstoquePeca:
    """Quantidades de uma peça: a física, a reservada e o saldo disponível (RF-12, RF-18).

    É um agregado separado de `Peca`, na relação 1:1, para a reserva, a baixa e o estorno
    bloquearem só este registro. O saldo disponível nunca fica negativo, e todo aumento dele
    acumula um `SaldoPecaAtualizadoEvent` para a alocação às OS com peça pendente (RF-19).
    """

    peca_id: UUID
    quantidade_fisica: int = 0
    quantidade_reservada: int = 0
    _domain_events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.peca_id, UUID):
            raise PecaInvalida("a peça do estoque é obrigatória")
        _exigir_nao_negativa(self.quantidade_fisica)
        _exigir_nao_negativa(self.quantidade_reservada)
        if self.quantidade_reservada > self.quantidade_fisica:
            raise QuantidadeInvalida("a quantidade reservada não pode passar da física")

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, EstoquePeca) and outro.peca_id == self.peca_id

    def __hash__(self) -> int:
        return hash(self.peca_id)

    def saldo_disponivel(self) -> int:
        return self.quantidade_fisica - self.quantidade_reservada

    def reservar(self, quantidade: int) -> tuple[int, int]:
        """Reserva o menor valor entre o pedido e o saldo; devolve (reservada, pendente) (RF-18)."""
        _exigir_positiva(quantidade)
        reservada = min(quantidade, self.saldo_disponivel())
        self.quantidade_reservada += reservada
        return reservada, quantidade - reservada

    def alocar_pendencias(self, pendencias: Iterable[PendenciaPeca]) -> list[AlocacaoPeca]:
        """Reserva o saldo para a OS mais antiga primeiro e devolve o que cada uma recebeu (RF-19).

        Atende a conclusão do orçamento, com a OS nova entre as pendências, e o aumento de saldo.
        Em caso de empate na data de abertura vale a ordem recebida. Só devolve as OS que
        receberam alguma quantidade, e as reservas já feitas nunca são remanejadas. Se uma
        pendência for inválida, nada é reservado.
        """
        pendencias = list(pendencias)
        _exigir_pendencias_validas(pendencias)
        alocacoes = []
        for pendencia in sorted(pendencias, key=lambda p: p.data_abertura_os):
            reservada, _ = self.reservar(pendencia.quantidade_pendente)
            if reservada:
                alocacoes.append(AlocacaoPeca(pendencia.os_id, reservada))
        return alocacoes

    def baixar(self, quantidade: int) -> None:
        """Baixa definitiva de peças reservadas, no início da execução da OS (RF-20)."""
        _exigir_positiva(quantidade)
        self._exigir_reservada(quantidade)
        self.quantidade_fisica -= quantidade
        self.quantidade_reservada -= quantidade

    def estornar(self, quantidade: int) -> None:
        """Devolve reservas ao saldo, na rejeição do orçamento ou no cancelamento da OS (RF-18)."""
        _exigir_positiva(quantidade)
        self._exigir_reservada(quantidade)
        self.quantidade_reservada -= quantidade
        self._acumular_saldo_atualizado()

    def repor(self, quantidade: int) -> None:
        _exigir_positiva(quantidade)
        self.quantidade_fisica += quantidade
        self._acumular_saldo_atualizado()

    def ajustar_quantidade_fisica(self, nova_quantidade: int) -> None:
        """Corrige a quantidade física por perda, quebra ou inventário (RF-12)."""
        _exigir_nao_negativa(nova_quantidade)
        if nova_quantidade < self.quantidade_reservada:
            raise QuantidadeFisicaAbaixoDaReservada(nova_quantidade, self.quantidade_reservada)
        saldo_aumentou = nova_quantidade > self.quantidade_fisica
        self.quantidade_fisica = nova_quantidade
        if saldo_aumentou:
            self._acumular_saldo_atualizado()

    def collect_domain_events(self) -> list[DomainEvent]:
        eventos, self._domain_events = self._domain_events, []
        return eventos

    def _exigir_reservada(self, quantidade: int) -> None:
        if quantidade > self.quantidade_reservada:
            raise SaldoInsuficiente(str(self.peca_id), quantidade, self.quantidade_reservada)

    def _acumular_saldo_atualizado(self) -> None:
        self._domain_events.append(
            SaldoPecaAtualizadoEvent(peca_id=self.peca_id, saldo_disponivel=self.saldo_disponivel())
        )


def _exigir_pendencias_validas(pendencias: list) -> None:
    if not all(isinstance(pendencia, PendenciaPeca) for pendencia in pendencias):
        raise AlocacaoInvalida("as pendências devem ser objetos PendenciaPeca")
    if len({pendencia.os_id for pendencia in pendencias}) != len(pendencias):
        raise AlocacaoInvalida("a mesma OS não pode ter duas pendências da peça")


def _exigir_positiva(quantidade: object) -> None:
    if type(quantidade) is not int or quantidade <= 0:
        raise QuantidadeInvalida("deve ser um número inteiro maior que zero")


def _exigir_nao_negativa(quantidade: object) -> None:
    if type(quantidade) is not int or quantidade < 0:
        raise QuantidadeInvalida("deve ser um número inteiro maior ou igual a zero")
