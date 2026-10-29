from uuid import uuid4

import pytest

from domain.entities.estoque_peca import EstoquePeca
from domain.repositories.estoque_repository import EstoqueRepository


class EstoqueRepositoryEmMemoria(EstoqueRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, estoque):
        self.dados[estoque.peca_id] = estoque

    async def buscar_por_peca(self, peca_id):
        return self.dados.get(peca_id)


def test_porta_define_salvar_e_busca_por_peca():
    assert EstoqueRepository.__abstractmethods__ == {"salvar", "buscar_por_peca"}


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemBuscaPorPeca(EstoqueRepository):
        async def salvar(self, estoque): ...

    with pytest.raises(TypeError):
        SemBuscaPorPeca()


async def test_salva_e_busca_o_estoque_pela_peca():
    repositorio = EstoqueRepositoryEmMemoria()
    estoque = EstoquePeca(peca_id=uuid4(), quantidade_fisica=10)
    await repositorio.salvar(estoque)

    estoque.reservar(4)
    await repositorio.salvar(estoque)

    encontrado = await repositorio.buscar_por_peca(estoque.peca_id)
    assert encontrado == estoque
    assert encontrado.quantidade_reservada == 4
    assert await repositorio.buscar_por_peca(uuid4()) is None
