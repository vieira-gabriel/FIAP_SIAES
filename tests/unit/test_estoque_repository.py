from uuid import uuid4

import pytest

from domain.entities.estoque_peca import EstoquePeca
from domain.repositories.estoque_repository import EstoqueRepository


def test_porta_define_salvar_e_buscas_por_peca():
    assert EstoqueRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_peca",
        "buscar_por_pecas",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemBuscaPorPeca(EstoqueRepository):
        async def salvar(self, estoque): ...

    with pytest.raises(TypeError):
        SemBuscaPorPeca()


async def test_salva_e_busca_o_estoque_pela_peca(estoques):
    estoque = EstoquePeca(peca_id=uuid4(), quantidade_fisica=10)
    await estoques.salvar(estoque)

    estoque.reservar(4)
    await estoques.salvar(estoque)

    encontrado = await estoques.buscar_por_peca(estoque.peca_id)
    assert encontrado == estoque
    assert encontrado.quantidade_reservada == 4
    assert await estoques.buscar_por_peca(uuid4()) is None


async def test_busca_o_estoque_de_varias_pecas_e_ignora_as_sem_estoque(estoques):
    filtro = EstoquePeca(peca_id=uuid4(), quantidade_fisica=10)
    vela = EstoquePeca(peca_id=uuid4(), quantidade_fisica=4)
    for estoque in (filtro, vela):
        await estoques.salvar(estoque)
    sem_estoque = uuid4()

    encontrados = await estoques.buscar_por_pecas([filtro.peca_id, sem_estoque])

    assert encontrados == {filtro.peca_id: filtro}
