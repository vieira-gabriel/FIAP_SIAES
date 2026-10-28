import pytest

from application.ports.password_hasher import PasswordHasher
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.peca_repository import PecaRepository
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


class PecaRepositoryEmMemoria(PecaRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, peca):
        self.dados[peca.id] = peca

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_codigo_referencia(self, codigo_referencia):
        return next(
            (p for p in self.dados.values() if p.codigo_referencia == codigo_referencia), None
        )

    async def listar(self):
        return sorted((p for p in self.dados.values() if p.ativo), key=lambda p: p.nome)


@pytest.fixture
def pecas() -> PecaRepositoryEmMemoria:
    return PecaRepositoryEmMemoria()


class EstoqueRepositoryEmMemoria(EstoqueRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, estoque):
        self.dados[estoque.peca_id] = estoque

    async def buscar_por_peca(self, peca_id):
        return self.dados.get(peca_id)

    async def buscar_por_pecas(self, peca_ids):
        return {id: self.dados[id] for id in peca_ids if id in self.dados}


@pytest.fixture
def estoques() -> EstoqueRepositoryEmMemoria:
    return EstoqueRepositoryEmMemoria()


class OrdemServicoRepositoryEmMemoria(OrdemServicoRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, os):
        self.dados[os.id] = os

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_numero(self, numero):
        return next((os for os in self.dados.values() if os.numero == numero), None)

    async def listar_pendentes_da_peca(self, peca_id):
        pendentes = [
            os
            for os in self.dados.values()
            if any(i.peca_id == peca_id and i.quantidade_pendente > 0 for i in os.pecas)
        ]
        return sorted(pendentes, key=lambda os: os.data_abertura)


@pytest.fixture
def ordens() -> OrdemServicoRepositoryEmMemoria:
    return OrdemServicoRepositoryEmMemoria()
