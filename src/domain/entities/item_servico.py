from dataclasses import dataclass
from uuid import UUID

from domain.entities.servico import Servico
from domain.exceptions import OrdemServicoInvalida
from domain.value_objects.valor import Valor


@dataclass(eq=False)
class ItemServico:
    """Serviço incluído em uma OS, com nome, preço e tempo estimado copiados do catálogo (RF-17).

    Na conclusão do orçamento os valores são atualizados com os vigentes; a partir daí, reajustes
    no catálogo não os alteram (RNF-11).
    """

    servico_id: UUID
    nome: str
    preco_congelado: Valor
    tempo_estimado_minutos: int

    @classmethod
    def a_partir_de(cls, servico: Servico) -> "ItemServico":
        return cls(
            servico_id=servico.id,
            nome=servico.nome,
            preco_congelado=servico.valor_base,
            tempo_estimado_minutos=servico.tempo_estimado_minutos,
        )

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, ItemServico) and outro.servico_id == self.servico_id

    def __hash__(self) -> int:
        return hash(self.servico_id)

    def congelar(self, servico: Servico) -> None:
        if servico.id != self.servico_id:
            raise OrdemServicoInvalida("o serviço informado não é o do item")
        self.nome = servico.nome
        self.preco_congelado = servico.valor_base
        self.tempo_estimado_minutos = servico.tempo_estimado_minutos
