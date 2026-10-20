from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.exceptions import UsuarioInvalido
from domain.value_objects.perfil_usuario import PerfilUsuario


@dataclass(eq=False)
class Usuario:
    """Usuário interno da oficina: Atendente, Mecânico ou Gerente (RF-01 a RF-03).

    Guarda apenas o hash da senha (RF-03, RNF-06); gerar e verificar o hash é papel
    da porta `PasswordHasher`, na camada de aplicação.
    """

    nome: str
    email: str
    senha_hash: str
    perfil: PerfilUsuario
    ativo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        self.nome = self.nome.strip()
        self.email = self.email.strip().lower()
        if not self.nome:
            raise UsuarioInvalido("o nome é obrigatório")
        if "@" not in self.email:
            raise UsuarioInvalido("o e-mail é obrigatório e deve conter '@'")
        if not self.senha_hash:
            raise UsuarioInvalido("o hash da senha é obrigatório")
        if not isinstance(self.perfil, PerfilUsuario):
            raise UsuarioInvalido("perfil desconhecido")

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, Usuario) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def desativar(self) -> None:
        self.ativo = False

    def reativar(self) -> None:
        self.ativo = True

    def alterar_senha_hash(self, senha_hash: str) -> None:
        if not senha_hash:
            raise UsuarioInvalido("o hash da senha é obrigatório")
        self.senha_hash = senha_hash

    def pode_autenticar(self) -> bool:
        """Usuário desativado pelo Gerente não faz login (RF-03)."""
        return self.ativo
