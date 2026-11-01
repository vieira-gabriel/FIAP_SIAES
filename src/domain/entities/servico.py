from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.exceptions import ServicoInvalido
from domain.value_objects.texto_livre import exigir_sem_marcacao
from domain.value_objects.valor import Valor


@dataclass(eq=False)
class Servico:
    """Serviço do catálogo da oficina (RF-10, RF-11).

    O valor base e o tempo estimado são copiados para o `ItemServico` na conclusão do
    orçamento; alterá-los aqui não muda as OS já orçadas (RF-17).
    """

    codigo: str
    nome: str
    descricao: str
    valor_base: Valor
    tempo_estimado_minutos: int
    ativo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        self._aplicar_dados(
            self.codigo, self.nome, self.descricao, self.valor_base, self.tempo_estimado_minutos
        )

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, Servico) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def atualizar_dados(
        self,
        codigo: str,
        nome: str,
        descricao: str,
        valor_base: Valor,
        tempo_estimado_minutos: int,
    ) -> None:
        self._aplicar_dados(codigo, nome, descricao, valor_base, tempo_estimado_minutos)

    def excluir(self) -> None:
        """Exclusão lógica: as OS que já incluem o serviço continuam íntegras (RF-11)."""
        self.ativo = False

    def pode_ser_incluido_em_os(self) -> bool:
        return self.ativo

    def _aplicar_dados(
        self,
        codigo: str,
        nome: str,
        descricao: str,
        valor_base: Valor,
        tempo_estimado_minutos: int,
    ) -> None:
        codigo, nome, descricao = codigo.strip(), nome.strip(), descricao.strip()
        if not codigo:
            raise ServicoInvalido("o código é obrigatório")
        if not nome:
            raise ServicoInvalido("o nome é obrigatório")
        if not descricao:
            raise ServicoInvalido("a descrição técnica é obrigatória")
        exigir_sem_marcacao(ServicoInvalido, codigo=codigo, nome=nome, descricao=descricao)
        if not isinstance(valor_base, Valor):
            raise ServicoInvalido("o valor base é obrigatório")
        if type(tempo_estimado_minutos) is not int or tempo_estimado_minutos < 0:
            raise ServicoInvalido("o tempo estimado deve ser um número inteiro de minutos ≥ 0")
        self.codigo, self.nome, self.descricao = codigo, nome, descricao
        self.valor_base, self.tempo_estimado_minutos = valor_base, tempo_estimado_minutos
