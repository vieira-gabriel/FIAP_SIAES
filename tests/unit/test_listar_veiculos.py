from uuid import uuid4

from application.use_cases.listar_veiculos import ListarVeiculos
from domain.entities.veiculo import Veiculo
from domain.value_objects.placa import Placa


def _veiculo(placa, cliente_id):
    return Veiculo(cliente_id=cliente_id, placa=Placa(placa), marca="Fiat", modelo="Uno", ano=2015)


async def test_lista_so_os_ativos_em_ordem_de_placa(veiculos):
    cliente_id = uuid4()
    excluido = _veiculo("AAA1111", cliente_id)
    excluido.excluir()
    for veiculo in (_veiculo("XYZ9876", cliente_id), excluido, _veiculo("ABC1D23", cliente_id)):
        await veiculos.salvar(veiculo)

    listados = await ListarVeiculos(veiculos).executar()

    assert [v.placa.valor for v in listados] == ["ABC1D23", "XYZ9876"]


async def test_filtra_pelo_cliente(veiculos):
    maria, joao = uuid4(), uuid4()
    await veiculos.salvar(_veiculo("ABC1D23", maria))
    await veiculos.salvar(_veiculo("XYZ9876", joao))

    listados = await ListarVeiculos(veiculos).executar(maria)

    assert [v.cliente_id for v in listados] == [maria]


async def test_cliente_sem_veiculos_devolve_lista_vazia(veiculos):
    await veiculos.salvar(_veiculo("ABC1D23", uuid4()))

    assert await ListarVeiculos(veiculos).executar(uuid4()) == []
