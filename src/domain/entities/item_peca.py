from dataclasses import dataclass
from uuid import UUID

from domain.entities.peca import Peca
from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.valor import Valor


@dataclass(eq=False)
class ItemPeca:
    """Peça incluída em uma OS, com nome, preço e prazo de reposição copiados do catálogo (RF-17).

    Na conclusão do orçamento os valores são atualizados com os vigentes; a partir daí, reajustes
    no catálogo não os alteram (RNF-11). A reserva e a pendência nascem zeradas e são definidas
    pela reserva de estoque (RF-18).
    """

    peca_id: UUID
    nome: str
    quantidade: int
    preco_unitario_congelado: Valor
    prazo_reposicao_dias: int
    quantidade_reservada: int = 0
    quantidade_pendente: int = 0

    def __post_init__(self):
        if type(self.quantidade) is not int or self.quantidade <= 0:
            raise OrdemServicoInvalida("a quantidade deve ser um número inteiro maior que zero")
        for quantidade in (self.quantidade_reservada, self.quantidade_pendente):
            if type(quantidade) is not int or quantidade < 0:
                raise OrdemServicoInvalida("reservada e pendente não podem ser negativas")
        if self.quantidade_reservada + self.quantidade_pendente > self.quantidade:
            raise OrdemServicoInvalida("reservada mais pendente não pode passar da quantidade")

    @classmethod
    def a_partir_de(cls, peca: Peca, quantidade: int) -> "ItemPeca":
        return cls(
            peca_id=peca.id,
            nome=peca.nome,
            quantidade=quantidade,
            preco_unitario_congelado=peca.preco_unitario,
            prazo_reposicao_dias=peca.prazo_reposicao_dias,
        )

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, ItemPeca) and outro.peca_id == self.peca_id

    def __hash__(self) -> int:
        return hash(self.peca_id)

    def valor_total(self) -> Valor:
        return self.preco_unitario_congelado.multiplicar(self.quantidade)

    def congelar(self, peca: Peca) -> None:
        if peca.id != self.peca_id:
            raise OrdemServicoInvalida("a peça informada não é a do item")
        self.nome = peca.nome
        self.preco_unitario_congelado = peca.preco_unitario
        self.prazo_reposicao_dias = peca.prazo_reposicao_dias
