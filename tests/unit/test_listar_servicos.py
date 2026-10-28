from application.use_cases.listar_servicos import ListarServicos
from domain.entities.servico import Servico
from domain.value_objects.valor import Valor


def _servico(codigo, nome):
    return Servico(
        codigo=codigo,
        nome=nome,
        descricao="Descrição técnica",
        valor_base=Valor("100"),
        tempo_estimado_minutos=30,
    )


async def test_lista_so_os_servicos_ativos_em_ordem_de_nome(servicos):
    troca = _servico("SRV-001", "Troca de óleo")
    alinhamento = _servico("SRV-002", "Alinhamento")
    excluido = _servico("SRV-003", "Balanceamento")
    excluido.excluir()
    for servico in (troca, alinhamento, excluido):
        await servicos.salvar(servico)

    assert await ListarServicos(servicos).executar() == [alinhamento, troca]


async def test_catalogo_vazio(servicos):
    assert await ListarServicos(servicos).executar() == []
