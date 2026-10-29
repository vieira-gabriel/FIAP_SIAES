from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.exceptions import AlteracaoDoProprioAcesso, UsuarioInvalido
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
        self.nome, self.email = _nome_e_email_validos(self.nome, self.email)
        if not self.senha_hash:
            raise UsuarioInvalido("o hash da senha é obrigatório")
        _validar_perfil(self.perfil)

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, Usuario) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def atualizar_dados(self, nome: str, email: str) -> None:
        self.nome, self.email = _nome_e_email_validos(nome, email)

    def alterar_perfil(self, perfil: PerfilUsuario, responsavel_id: UUID) -> None:
        """O Gerente não muda o próprio perfil, para a oficina não ficar sem Gerente (RF-03)."""
        _validar_perfil(perfil)
        if perfil != self.perfil and responsavel_id == self.id:
            raise AlteracaoDoProprioAcesso("alterar o próprio perfil")
        self.perfil = perfil

    def desativar_por(self, responsavel_id: UUID) -> None:
        """O Gerente não desativa o próprio acesso, para a oficina não ficar sem Gerente (RF-03)."""
        if responsavel_id == self.id:
            raise AlteracaoDoProprioAcesso("desativar o próprio acesso")
        self.desativar()

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


def _nome_e_email_validos(nome: str, email: str) -> tuple[str, str]:
    nome, email = nome.strip(), email.strip().lower()
    if not nome:
        raise UsuarioInvalido("o nome é obrigatório")
    if "@" not in email:
        raise UsuarioInvalido("o e-mail é obrigatório e deve conter '@'")
    return nome, email


def _validar_perfil(perfil: PerfilUsuario) -> None:
    if not isinstance(perfil, PerfilUsuario):
        raise UsuarioInvalido("perfil desconhecido")
