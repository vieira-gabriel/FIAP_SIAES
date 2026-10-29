from application.use_cases.cadastrar_peca import CadastrarPeca
from application.use_cases.listar_pecas import ListarPecas
from domain.value_objects.valor import Valor


async def test_lista_as_ativas_em_ordem_de_nome_com_o_estoque(pecas, estoques):
    cadastrar = CadastrarPeca(pecas, estoques)
    vela = await cadastrar.executar("VEL-001", "Vela de ignição", Valor("20.00"), 2)
    filtro = await cadastrar.executar("FLT-001", "Filtro de óleo", Valor("35.90"), 3)
    excluida, _ = await cadastrar.executar("PAS-001", "Pastilha de freio", Valor("90.00"), 5)
    excluida.excluir([])

    assert await ListarPecas(pecas, estoques).executar() == [filtro, vela]


async def test_sem_pecas_devolve_lista_vazia(pecas, estoques):
    assert await ListarPecas(pecas, estoques).executar() == []
