from uuid import uuid4

import pytest

from application.use_cases.cadastrar_peca import CadastrarPeca
from application.use_cases.excluir_peca import ExcluirPeca
from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada, PecaComPendencia
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor


async def _cadastrar(pecas, estoques):
    return await CadastrarPeca(pecas, estoques).executar(
        "FLT-001", "Filtro de óleo", Valor("35.90"), 3, quantidade_fisica_inicial=5
    )


def _os_com_a_peca(peca, quantidade_pendente):
    item = ItemPeca(
        peca_id=peca.id,
        nome=peca.nome,
        quantidade=3,
        preco_unitario_congelado=peca.preco_unitario,
        prazo_reposicao_dias=peca.prazo_reposicao_dias,
        quantidade_pendente=quantidade_pendente,
    )
    return OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=StatusOS.AGUARDANDO_PECA,
        pecas=[item],
    )


async def test_exclusao_logica_mantem_as_reservas(pecas, estoques, ordens):
    peca, estoque = await _cadastrar(pecas, estoques)
    estoque.reservar(3)
    await ordens.salvar(_os_com_a_peca(peca, quantidade_pendente=0))

    await ExcluirPeca(pecas, estoques, ordens).executar(peca.id)

    assert not (await pecas.buscar_por_id(peca.id)).ativo
    assert (await estoques.buscar_por_peca(peca.id)).quantidade_reservada == 3


async def test_peca_pendente_em_alguma_os_nao_e_excluida(pecas, estoques, ordens):
    peca, _ = await _cadastrar(pecas, estoques)
    await ordens.salvar(_os_com_a_peca(peca, quantidade_pendente=1))

    with pytest.raises(PecaComPendencia) as erro:
        await ExcluirPeca(pecas, estoques, ordens).executar(peca.id)

    assert erro.value.numeros_das_os == ["529-7F3A9C2B"]
    assert (await pecas.buscar_por_id(peca.id)).ativo


async def test_excluir_de_novo_nao_encontra_a_peca(pecas, estoques, ordens):
    peca, _ = await _cadastrar(pecas, estoques)
    await ExcluirPeca(pecas, estoques, ordens).executar(peca.id)

    with pytest.raises(EntidadeNaoEncontrada):
        await ExcluirPeca(pecas, estoques, ordens).executar(peca.id)


async def test_bloqueia_o_estoque_antes_de_consultar_as_pendencias(pecas, estoques, ordens):
    """A leitura do estoque bloqueia o registro no PostgreSQL (RNF-09); a ordem importa."""
    peca, _ = await _cadastrar(pecas, estoques)
    chamadas = []
    buscar_estoque, listar_pendentes = estoques.buscar_por_peca, ordens.listar_pendentes_da_peca

    async def registrar_estoque(peca_id):
        chamadas.append("estoque")
        return await buscar_estoque(peca_id)

    async def registrar_pendentes(peca_id):
        chamadas.append("pendentes")
        return await listar_pendentes(peca_id)

    estoques.buscar_por_peca, ordens.listar_pendentes_da_peca = (
        registrar_estoque,
        registrar_pendentes,
    )

    await ExcluirPeca(pecas, estoques, ordens).executar(peca.id)

    assert chamadas == ["estoque", "pendentes"]
