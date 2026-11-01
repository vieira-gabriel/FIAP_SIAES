from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.exceptions import ClienteInvalido
from domain.value_objects.documento import Documento
from domain.value_objects.texto_livre import exigir_sem_marcacao


@dataclass(eq=False)
class Cliente:
    """Pessoa física ou jurídica proprietária do veículo (RF-04 a RF-06)."""

    nome: str
    documento: Documento
    email: str
    telefone: str
    ativo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        self._aplicar_dados(self.nome, self.documento, self.email, self.telefone)

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, Cliente) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def atualizar_dados(self, nome: str, documento: Documento, email: str, telefone: str) -> None:
        self._aplicar_dados(nome, documento, email, telefone)

    def excluir(self) -> None:
        """Exclusão lógica: as ordens de serviço do cliente continuam no histórico (RF-06)."""
        self.ativo = False

    def _aplicar_dados(self, nome: str, documento: Documento, email: str, telefone: str) -> None:
        nome = nome.strip()
        email = email.strip().lower()
        telefone = telefone.strip()
        if not nome:
            raise ClienteInvalido("o nome ou a razão social é obrigatório")
        if not isinstance(documento, Documento):
            raise ClienteInvalido("o documento deve ser um CPF ou CNPJ")
        if "@" not in email:
            raise ClienteInvalido("o e-mail é obrigatório e deve conter '@'")
        if not telefone:
            raise ClienteInvalido("o telefone é obrigatório")
        exigir_sem_marcacao(ClienteInvalido, nome=nome, email=email, telefone=telefone)
        self.nome, self.documento, self.email, self.telefone = nome, documento, email, telefone
