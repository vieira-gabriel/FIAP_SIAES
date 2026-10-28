from uuid import uuid4

import pytest

from domain.entities.peca import Peca
from domain.repositories.peca_repository import PecaRepository
from domain.value_objects.valor import Valor


class PecaRepositoryEmMemoria(PecaRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, peca):
        self.dados[peca.id] = peca

    async def buscar_por_id(self, id):
        return self.dados.get(id)

    async def buscar_por_codigo_referencia(self, codigo_referencia):
        return next(
            (p for p in self.dados.values() if p.codigo_referencia == codigo_referencia), None
        )

    async def listar(self):
        return sorted((p for p in self.dados.values() if p.ativo), key=lambda p: p.nome)


def criar_peca(codigo_referencia="FLT-001", nome="Filtro de óleo"):
    return Peca(
        codigo_referencia=codigo_referencia,
        nome=nome,
        preco_unitario=Valor("35.00"),
        prazo_reposicao_dias=3,
    )


def test_porta_define_salvar_buscas_e_listagem():
    assert PecaRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_codigo_referencia",
        "listar",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemListagem(PecaRepository):
        async def salvar(self, peca): ...

        async def buscar_por_id(self, id): ...

        async def buscar_por_codigo_referencia(self, codigo_referencia): ...

    with pytest.raises(TypeError):
        SemListagem()


async def test_salva_e_busca_a_peca_pelo_id_e_pelo_codigo_mesmo_excluida():
    repositorio = PecaRepositoryEmMemoria()
    peca = criar_peca()
    peca.excluir()
    await repositorio.salvar(peca)

    assert await repositorio.buscar_por_id(peca.id) == peca
    assert await repositorio.buscar_por_codigo_referencia("FLT-001") == peca
    assert await repositorio.buscar_por_id(uuid4()) is None
    assert await repositorio.buscar_por_codigo_referencia("XXX-999") is None


async def test_lista_so_as_ativas_em_ordem_de_nome():
    repositorio = PecaRepositoryEmMemoria()
    vela = criar_peca("VEL-001", "Vela de ignição")
    filtro = criar_peca("FLT-001", "Filtro de óleo")
    excluida = criar_peca("PAS-001", "Pastilha de freio")
    excluida.excluir()
    for peca in (vela, excluida, filtro):
        await repositorio.salvar(peca)

    assert await repositorio.listar() == [filtro, vela]
