from uuid import uuid4

import pytest

from application.use_cases.incluir_peca_na_os import IncluirPecaNaOS
from application.use_cases.incluir_servico_na_os import IncluirServicoNaOS
from application.use_cases.remover_peca_da_os import RemoverPecaDaOS
from application.use_cases.remover_servico_da_os import RemoverServicoDaOS
from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.exceptions import (
    EntidadeNaoEncontrada,
    ItemIndisponivel,
    ItemJaIncluido,
    ItensBloqueados,
    OrdemServicoInvalida,
)
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor


def _servico() -> Servico:
    return Servico(
        codigo="SRV-001",
        nome="Troca de óleo",
        descricao="Troca do óleo do motor",
        valor_base=Valor("120.00"),
        tempo_estimado_minutos=45,
    )


def _peca() -> Peca:
    return Peca(
        codigo_referencia="FLT-001",
        nome="Filtro de óleo",
        preco_unitario=Valor("35.90"),
        prazo_reposicao_dias=3,
    )


async def _os(ordens, status: StatusOS = StatusOS.EM_DIAGNOSTICO) -> OrdemServico:
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=status,
    )
    await ordens.salvar(os)
    return os


@pytest.fixture
def incluir_servico(ordens, servicos):
    return IncluirServicoNaOS(ordens, servicos)


@pytest.fixture
def incluir_peca(ordens, pecas):
    return IncluirPecaNaOS(ordens, pecas)


async def test_inclui_o_servico_do_catalogo_e_salva_a_os(incluir_servico, ordens, servicos):
    servico = _servico()
    await servicos.salvar(servico)
    os = await _os(ordens)

    await incluir_servico.executar(os.id, servico.id)

    salva = await ordens.buscar_por_id(os.id)
    assert [item.servico_id for item in salva.servicos] == [servico.id]
    assert salva.servicos[0].preco_congelado == Valor("120.00")


async def test_inclui_a_peca_do_catalogo_com_a_quantidade_e_salva_a_os(incluir_peca, ordens, pecas):
    peca = _peca()
    await pecas.salvar(peca)
    os = await _os(ordens)

    await incluir_peca.executar(os.id, peca.id, 3)

    (item,) = (await ordens.buscar_por_id(os.id)).pecas
    assert (item.peca_id, item.quantidade) == (peca.id, 3)


async def test_os_ou_item_do_catalogo_inexistente_responde_nao_encontrado(
    incluir_servico, incluir_peca, ordens, servicos, pecas
):
    os = await _os(ordens)
    servico, peca = _servico(), _peca()
    await servicos.salvar(servico)
    await pecas.salvar(peca)

    with pytest.raises(EntidadeNaoEncontrada):
        await incluir_servico.executar(uuid4(), servico.id)
    with pytest.raises(EntidadeNaoEncontrada):
        await incluir_servico.executar(os.id, uuid4())
    with pytest.raises(EntidadeNaoEncontrada):
        await incluir_peca.executar(uuid4(), peca.id, 1)
    with pytest.raises(EntidadeNaoEncontrada):
        await incluir_peca.executar(os.id, uuid4(), 1)

    salva = await ordens.buscar_por_id(os.id)
    assert (salva.servicos, salva.pecas) == ([], [])


async def test_servico_e_peca_excluidos_nao_entram_na_os(
    incluir_servico, incluir_peca, ordens, servicos, pecas
):
    servico, peca = _servico(), _peca()
    servico.excluir()
    peca.excluir([])
    await servicos.salvar(servico)
    await pecas.salvar(peca)
    os = await _os(ordens)

    with pytest.raises(ItemIndisponivel):
        await incluir_servico.executar(os.id, servico.id)
    with pytest.raises(ItemIndisponivel):
        await incluir_peca.executar(os.id, peca.id, 1)

    salva = await ordens.buscar_por_id(os.id)
    assert (salva.servicos, salva.pecas) == ([], [])


async def test_item_repetido_e_recusado(incluir_servico, incluir_peca, ordens, servicos, pecas):
    servico, peca = _servico(), _peca()
    await servicos.salvar(servico)
    await pecas.salvar(peca)
    os = await _os(ordens)
    await incluir_servico.executar(os.id, servico.id)
    await incluir_peca.executar(os.id, peca.id, 1)

    with pytest.raises(ItemJaIncluido):
        await incluir_servico.executar(os.id, servico.id)
    with pytest.raises(ItemJaIncluido):
        await incluir_peca.executar(os.id, peca.id, 2)

    salva = await ordens.buscar_por_id(os.id)
    assert (len(salva.servicos), len(salva.pecas)) == (1, 1)


@pytest.mark.parametrize("quantidade", [0, -1, True, 1.5, "2", None])
async def test_quantidade_da_peca_precisa_ser_inteiro_maior_que_zero(
    incluir_peca, ordens, pecas, quantidade
):
    peca = _peca()
    await pecas.salvar(peca)
    os = await _os(ordens)

    with pytest.raises(OrdemServicoInvalida):
        await incluir_peca.executar(os.id, peca.id, quantidade)

    assert (await ordens.buscar_por_id(os.id)).pecas == []


@pytest.mark.parametrize(
    "status", [status for status in StatusOS if status is not StatusOS.EM_DIAGNOSTICO]
)
async def test_so_inclui_e_remove_itens_em_diagnostico(
    incluir_servico, incluir_peca, ordens, servicos, pecas, status
):
    servico, peca = _servico(), _peca()
    await servicos.salvar(servico)
    await pecas.salvar(peca)
    os = await _os(ordens, status)

    with pytest.raises(ItensBloqueados):
        await incluir_servico.executar(os.id, servico.id)
    with pytest.raises(ItensBloqueados):
        await incluir_peca.executar(os.id, peca.id, 1)
    with pytest.raises(ItensBloqueados):
        await RemoverServicoDaOS(ordens).executar(os.id, servico.id)
    with pytest.raises(ItensBloqueados):
        await RemoverPecaDaOS(ordens).executar(os.id, peca.id)


async def test_remove_o_servico_e_a_peca_da_os(
    incluir_servico, incluir_peca, ordens, servicos, pecas
):
    servico, peca = _servico(), _peca()
    await servicos.salvar(servico)
    await pecas.salvar(peca)
    os = await _os(ordens)
    await incluir_servico.executar(os.id, servico.id)
    await incluir_peca.executar(os.id, peca.id, 1)

    await RemoverServicoDaOS(ordens).executar(os.id, servico.id)
    await RemoverPecaDaOS(ordens).executar(os.id, peca.id)

    salva = await ordens.buscar_por_id(os.id)
    assert (salva.servicos, salva.pecas) == ([], [])


async def test_remover_item_que_nao_esta_na_os_ou_os_inexistente_responde_nao_encontrado(ordens):
    os = await _os(ordens)

    with pytest.raises(EntidadeNaoEncontrada):
        await RemoverServicoDaOS(ordens).executar(os.id, uuid4())
    with pytest.raises(EntidadeNaoEncontrada):
        await RemoverPecaDaOS(ordens).executar(os.id, uuid4())
    with pytest.raises(EntidadeNaoEncontrada):
        await RemoverServicoDaOS(ordens).executar(uuid4(), uuid4())
    with pytest.raises(EntidadeNaoEncontrada):
        await RemoverPecaDaOS(ordens).executar(uuid4(), uuid4())
