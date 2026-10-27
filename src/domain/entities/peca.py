from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.exceptions import PecaInvalida
from domain.value_objects.valor import Valor


@dataclass(eq=False)
class Peca:
    """Cadastro de uma peça ou insumo (RF-12).

    As quantidades ficam em `EstoquePeca`, na relação 1:1. O preço unitário e o prazo de
    reposição são copiados para o `ItemPeca` na conclusão do orçamento (RF-17).
    """

    codigo_referencia: str
    nome: str
    preco_unitario: Valor
    prazo_reposicao_dias: int
    ativo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        self._aplicar_dados(
            self.codigo_referencia, self.nome, self.preco_unitario, self.prazo_reposicao_dias
        )

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, Peca) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def atualizar_dados(
        self,
        codigo_referencia: str,
        nome: str,
        preco_unitario: Valor,
        prazo_reposicao_dias: int,
    ) -> None:
        self._aplicar_dados(codigo_referencia, nome, preco_unitario, prazo_reposicao_dias)

    def excluir(self) -> None:
        """Exclusão lógica: as reservas e as OS existentes continuam íntegras (RF-12)."""
        self.ativo = False

    def pode_ser_incluida_em_os(self) -> bool:
        return self.ativo

    def _aplicar_dados(
        self,
        codigo_referencia: str,
        nome: str,
        preco_unitario: Valor,
        prazo_reposicao_dias: int,
    ) -> None:
        codigo_referencia, nome = codigo_referencia.strip(), nome.strip()
        if not codigo_referencia:
            raise PecaInvalida("o código de referência é obrigatório")
        if not nome:
            raise PecaInvalida("o nome é obrigatório")
        if not isinstance(preco_unitario, Valor):
            raise PecaInvalida("o preço unitário é obrigatório")
        if type(prazo_reposicao_dias) is not int or prazo_reposicao_dias < 0:
            raise PecaInvalida("o prazo de reposição deve ser um número inteiro de dias ≥ 0")
        self.codigo_referencia, self.nome = codigo_referencia, nome
        self.preco_unitario, self.prazo_reposicao_dias = preco_unitario, prazo_reposicao_dias
