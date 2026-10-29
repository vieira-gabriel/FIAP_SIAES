from application.use_cases.listar_clientes import ListarClientes
from domain.entities.cliente import Cliente
from domain.value_objects.cpf import CPF


def _cliente(nome, documento):
    return Cliente(nome=nome, documento=CPF(documento), email="a@exemplo.com", telefone="11")


async def test_lista_so_os_clientes_ativos_em_ordem_de_nome(clientes):
    zeca = _cliente("Zeca", "52998224725")
    ana = _cliente("Ana", "11144477735")
    excluido = _cliente("Bruno", "12345678909")
    excluido.excluir()
    for cliente in (zeca, ana, excluido):
        await clientes.salvar(cliente)

    assert await ListarClientes(clientes).executar() == [ana, zeca]


async def test_lista_vazia(clientes):
    assert await ListarClientes(clientes).executar() == []
