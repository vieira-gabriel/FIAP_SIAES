from collections.abc import Collection
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.exceptions import PecaComPendencia, PecaInvalida
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.texto_livre import exigir_sem_marcacao
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

    def excluir(self, numeros_das_os_pendentes: Collection[NumeroOS]) -> None:
        """Exclusão lógica: as reservas e as OS existentes continuam íntegras (RF-12).

        Uma OS com quantidade pendente da peça depende da reposição dela, então a peça só pode
        ser excluída depois que nenhuma OS a espera.
        """
        if numeros_das_os_pendentes:
            raise PecaComPendencia(self.nome, [numero.valor for numero in numeros_das_os_pendentes])
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
        # Em maiúsculas para "flt-001" e "FLT-001" não virarem duas peças (RF-12).
        codigo_referencia, nome = codigo_referencia.strip().upper(), nome.strip()
        if not codigo_referencia:
            raise PecaInvalida("o código de referência é obrigatório")
        if not nome:
            raise PecaInvalida("o nome é obrigatório")
        exigir_sem_marcacao(PecaInvalida, codigo_referencia=codigo_referencia, nome=nome)
        if not isinstance(preco_unitario, Valor):
            raise PecaInvalida("o preço unitário é obrigatório")
        if type(prazo_reposicao_dias) is not int or prazo_reposicao_dias < 0:
            raise PecaInvalida("o prazo de reposição deve ser um número inteiro de dias ≥ 0")
        self.codigo_referencia, self.nome = codigo_referencia, nome
        self.preco_unitario, self.prazo_reposicao_dias = preco_unitario, prazo_reposicao_dias
