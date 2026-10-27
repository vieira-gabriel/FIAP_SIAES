import pytest

from domain.entities.cliente import Cliente
from domain.repositories.cliente_repository import ClienteRepository
from domain.value_objects.cpf import CPF


class ClienteRepositoryEmMemoria(ClienteRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, cliente):
        self.dados[cliente.id] = cliente

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_documento(self, documento):
        return next((c for c in self.dados.values() if c.documento == documento), None)


def test_porta_define_salvar_e_buscas_por_id_e_documento():
    assert ClienteRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_documento",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemBuscaPorDocumento(ClienteRepository):
        async def salvar(self, cliente): ...

        async def buscar_por_id(self, id): ...

    with pytest.raises(TypeError):
        SemBuscaPorDocumento()


async def test_busca_por_documento_independe_da_pontuacao_digitada():
    repositorio = ClienteRepositoryEmMemoria()
    cliente = Cliente(
        nome="Maria Silva",
        documento=CPF("529.982.247-25"),
        email="maria@exemplo.com",
        telefone="11987654321",
    )
    await repositorio.salvar(cliente)

    assert await repositorio.buscar_por_documento(CPF("52998224725")) == cliente
    assert await repositorio.buscar_por_id(cliente.id) == cliente
    assert await repositorio.buscar_por_documento(CPF("111.444.777-35")) is None
