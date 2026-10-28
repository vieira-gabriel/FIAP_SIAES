import pytest

from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.veiculo_repository import VeiculoRepository


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


class VeiculoRepositoryEmMemoria(VeiculoRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, veiculo):
        self.dados[veiculo.id] = veiculo

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_placa(self, placa):
        return next((v for v in self.dados.values() if v.ativo and v.placa == placa), None)

    async def listar(self, cliente_id=None):
        selecionados = (
            v
            for v in self.dados.values()
            if v.ativo and (cliente_id is None or v.cliente_id == cliente_id)
        )
        return sorted(selecionados, key=lambda veiculo: veiculo.placa.valor)


@pytest.fixture
def clientes() -> ClienteRepositoryEmMemoria:
    return ClienteRepositoryEmMemoria()


@pytest.fixture
def veiculos() -> VeiculoRepositoryEmMemoria:
    return VeiculoRepositoryEmMemoria()
