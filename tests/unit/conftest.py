import pytest

from application.ports.password_hasher import PasswordHasher
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.servico_repository import ServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository


class ClienteRepositoryEmMemoria(ClienteRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, cliente):
        self.dados[cliente.id] = cliente

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_documento(self, documento):
        return next((c for c in self.dados.values() if c.documento == documento), None)

    async def listar(self):
        ativos = (c for c in self.dados.values() if c.ativo)
        return sorted(ativos, key=lambda cliente: cliente.nome)


@pytest.fixture
def clientes() -> ClienteRepositoryEmMemoria:
    return ClienteRepositoryEmMemoria()


class UsuarioRepositoryEmMemoria(UsuarioRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, usuario):
        self.dados[usuario.id] = usuario

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_email(self, email):
        return next((u for u in self.dados.values() if u.email == email), None)

    async def listar(self):
        return sorted(self.dados.values(), key=lambda usuario: usuario.nome)


class PasswordHasherFalso(PasswordHasher):
    async def gerar_hash(self, senha):
        return f"hash:{senha}"

    async def verificar(self, senha, senha_hash):
        return senha_hash == f"hash:{senha}"


@pytest.fixture
def usuarios() -> UsuarioRepositoryEmMemoria:
    return UsuarioRepositoryEmMemoria()


@pytest.fixture
def password_hasher() -> PasswordHasherFalso:
    return PasswordHasherFalso()


class ServicoRepositoryEmMemoria(ServicoRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, servico):
        self.dados[servico.id] = servico

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_codigo(self, codigo):
        return next((s for s in self.dados.values() if s.codigo == codigo), None)

    async def listar(self):
        ativos = (s for s in self.dados.values() if s.ativo)
        return sorted(ativos, key=lambda servico: servico.nome)


@pytest.fixture
def servicos() -> ServicoRepositoryEmMemoria:
    return ServicoRepositoryEmMemoria()
