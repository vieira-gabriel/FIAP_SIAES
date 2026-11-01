from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.entities.item_peca import ItemPeca
from domain.entities.ordem_servico import OrdemServico
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

PECA_ID = uuid4()
AGORA = datetime.now(UTC)


def criar_os(numero="529-7F3A9C2B", data_abertura=AGORA, quantidade_pendente=0):
    item = ItemPeca(
        peca_id=PECA_ID,
        nome="Filtro de óleo",
        quantidade=2,
        preco_unitario_congelado=Valor("35.00"),
        prazo_reposicao_dias=3,
        quantidade_pendente=quantidade_pendente,
    )
    return OrdemServico(
        numero=NumeroOS(numero),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=StatusOS.AGUARDANDO_PECA,
        data_abertura=data_abertura,
        pecas=[item],
    )


def test_porta_define_salvar_buscas_e_pendencias_da_peca():
    assert OrdemServicoRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_numero",
        "listar",
        "listar_finalizadas",
        "listar_pendentes_da_peca",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemPendencias(OrdemServicoRepository):
        async def salvar(self, os): ...

        async def buscar_por_id(self, id): ...

        async def buscar_por_numero(self, numero): ...

    with pytest.raises(TypeError):
        SemPendencias()


async def test_salva_e_busca_a_os_pelo_id_e_pelo_numero(ordens):
    os = criar_os()
    await ordens.salvar(os)

    assert await ordens.buscar_por_id(os.id) == os
    assert await ordens.buscar_por_numero(NumeroOS("529-7F3A9C2B")) == os
    assert await ordens.buscar_por_id(uuid4()) is None
    assert await ordens.buscar_por_numero(NumeroOS("529-00000000")) is None


async def test_lista_as_pendentes_da_peca_da_mais_antiga_para_a_mais_nova(ordens):
    mais_nova = criar_os("529-00000002", AGORA, quantidade_pendente=2)
    mais_antiga = criar_os("529-00000001", AGORA - timedelta(days=1), quantidade_pendente=1)
    sem_pendencia = criar_os("529-00000003", AGORA - timedelta(days=2))
    for os in (mais_nova, sem_pendencia, mais_antiga):
        await ordens.salvar(os)

    assert await ordens.listar_pendentes_da_peca(PECA_ID) == [mais_antiga, mais_nova]
    assert await ordens.listar_pendentes_da_peca(uuid4()) == []
