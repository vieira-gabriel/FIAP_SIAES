from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from domain.entities.item_peca import ItemPeca
from domain.entities.item_servico import ItemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.exceptions import (
    EntidadeNaoEncontrada,
    ItemIndisponivel,
    ItemJaIncluido,
    ItensBloqueados,
    OrdemServicoInvalida,
)
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.orcamento import Orcamento
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor


@dataclass(eq=False)
class OrdemServico:
    """Raiz do agregado principal: o atendimento de um veículo, da abertura à entrega (RF-13).

    Os itens só mudam durante o diagnóstico e só aceitam serviços e peças ativos (RF-17). O
    orçamento soma os valores congelados nos itens (RNF-11).
    """

    numero: NumeroOS
    cliente_id: UUID
    veiculo_id: UUID
    atendente_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: StatusOS = StatusOS.RECEBIDA
    data_abertura: datetime = field(default_factory=lambda: datetime.now(UTC))
    servicos: list[ItemServico] = field(default_factory=list)
    pecas: list[ItemPeca] = field(default_factory=list)
    orcamento: Orcamento | None = None

    def __post_init__(self):
        if not isinstance(self.numero, NumeroOS):
            raise OrdemServicoInvalida("o número da OS é obrigatório")
        for nome, identificador in (
            ("o cliente", self.cliente_id),
            ("o veículo", self.veiculo_id),
            ("o atendente", self.atendente_id),
        ):
            if not isinstance(identificador, UUID):
                raise OrdemServicoInvalida(f"{nome} é obrigatório")
        if not isinstance(self.status, StatusOS):
            raise OrdemServicoInvalida("o status da OS é inválido")
        if not isinstance(self.data_abertura, datetime) or self.data_abertura.tzinfo is None:
            raise OrdemServicoInvalida("a data de abertura da OS deve ter fuso horário")

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, OrdemServico) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def incluir_servico(self, servico: Servico) -> None:
        self._exigir_itens_editaveis()
        if not servico.pode_ser_incluido_em_os():
            raise ItemIndisponivel(servico.nome)
        if any(item.servico_id == servico.id for item in self.servicos):
            raise ItemJaIncluido(servico.nome)
        self.servicos.append(ItemServico.a_partir_de(servico))
        self.orcamento = None

    def incluir_peca(self, peca: Peca, quantidade: int) -> None:
        self._exigir_itens_editaveis()
        if not peca.pode_ser_incluida_em_os():
            raise ItemIndisponivel(peca.nome)
        if any(item.peca_id == peca.id for item in self.pecas):
            raise ItemJaIncluido(peca.nome)
        self.pecas.append(ItemPeca.a_partir_de(peca, quantidade))
        self.orcamento = None

    def remover_servico(self, servico_id: UUID) -> None:
        self._exigir_itens_editaveis()
        item = next((item for item in self.servicos if item.servico_id == servico_id), None)
        if item is None:
            raise EntidadeNaoEncontrada("Item de serviço", servico_id)
        self.servicos.remove(item)
        self.orcamento = None

    def remover_peca(self, peca_id: UUID) -> None:
        self._exigir_itens_editaveis()
        item = next((item for item in self.pecas if item.peca_id == peca_id), None)
        if item is None:
            raise EntidadeNaoEncontrada("Item de peça", peca_id)
        self.pecas.remove(item)
        self.orcamento = None

    def congelar_valores(
        self, servicos_vigentes: Iterable[Servico], pecas_vigentes: Iterable[Peca]
    ) -> None:
        """Atualiza os itens com os valores vigentes do catálogo e calcula o orçamento (RF-17).

        O domínio não consulta o catálogo: o caso de uso entrega o `Servico` e a `Peca` de cada
        item. Se faltar algum, nenhum item é alterado. O orçamento vale até os itens mudarem:
        incluir ou remover um item o descarta, e só então o congelamento pode ser refeito.
        """
        self._exigir_itens_editaveis()
        servicos = {servico.id: servico for servico in servicos_vigentes}
        pecas = {peca.id: peca for peca in pecas_vigentes}
        sem_valor_vigente = [i.nome for i in self.servicos if i.servico_id not in servicos]
        sem_valor_vigente += [i.nome for i in self.pecas if i.peca_id not in pecas]
        if sem_valor_vigente:
            raise OrdemServicoInvalida(
                f"faltam os valores vigentes de: {', '.join(sem_valor_vigente)}"
            )
        for item_servico in self.servicos:
            item_servico.congelar(servicos[item_servico.servico_id])
        for item_peca in self.pecas:
            item_peca.congelar(pecas[item_peca.peca_id])
        self.orcamento = Orcamento(
            subtotal_servicos=_somar(item.preco_congelado for item in self.servicos),
            subtotal_pecas=_somar(item.valor_total() for item in self.pecas),
        )

    def _exigir_itens_editaveis(self) -> None:
        if self.status != StatusOS.EM_DIAGNOSTICO:
            raise ItensBloqueados(self.status)


def _somar(valores: Iterable[Valor]) -> Valor:
    total = Valor(0)
    for valor in valores:
        total = total.somar(valor)
    return total
