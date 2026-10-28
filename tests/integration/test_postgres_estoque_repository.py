"""Adaptadores de peça e estoque com PostgreSQL real (RF-12, RNF-09)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from domain.entities.estoque_peca import EstoquePeca
from domain.entities.peca import Peca
from domain.value_objects.valor import Valor
from infrastructure.database.engine import criar_fabrica_de_sessoes
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_estoque_repository import PostgresEstoqueRepository
from infrastructure.repositories.postgres_peca_repository import PostgresPecaRepository


@pytest.fixture
def fabrica_de_sessoes(banco_migrado):
    return criar_fabrica_de_sessoes(banco_migrado)


async def _cadastrar(fabrica_de_sessoes, codigo="FLT-001", quantidade_fisica=10):
    peca = Peca(
        codigo_referencia=codigo,
        nome="Filtro de óleo",
        preco_unitario=Valor("35.90"),
        prazo_reposicao_dias=3,
    )
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        await PostgresPecaRepository(unidade.sessao).salvar(peca)
        await PostgresEstoqueRepository(unidade.sessao).salvar(
            EstoquePeca(peca_id=peca.id, quantidade_fisica=quantidade_fisica)
        )
    return peca


async def test_peca_e_estoque_salvos_e_encontrados(fabrica_de_sessoes):
    filtro = await _cadastrar(fabrica_de_sessoes, "FLT-001", 10)
    vela = await _cadastrar(fabrica_de_sessoes, "VEL-001", 4)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        peca = await PostgresPecaRepository(unidade.sessao).buscar_por_codigo_referencia("FLT-001")
        estoques = PostgresEstoqueRepository(unidade.sessao)
        estoque = await estoques.buscar_por_peca(filtro.id)
        varios = await estoques.buscar_por_pecas([filtro.id, vela.id])

    assert (peca, peca.preco_unitario) == (filtro, Valor("35.90"))
    assert (estoque.quantidade_fisica, estoque.quantidade_reservada) == (10, 0)
    assert {id: e.quantidade_fisica for id, e in varios.items()} == {filtro.id: 10, vela.id: 4}


async def test_salvar_de_novo_atualiza_as_quantidades(fabrica_de_sessoes):
    peca = await _cadastrar(fabrica_de_sessoes)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        estoques = PostgresEstoqueRepository(unidade.sessao)
        estoque = await estoques.buscar_por_peca(peca.id)
        estoque.reservar(4)
        await estoques.salvar(estoque)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        salvo = await PostgresEstoqueRepository(unidade.sessao).buscar_por_peca(peca.id)

    assert (salvo.quantidade_fisica, salvo.quantidade_reservada) == (10, 4)


async def test_banco_recusa_reservada_acima_da_fisica(fabrica_de_sessoes):
    peca = await _cadastrar(fabrica_de_sessoes)

    with pytest.raises(IntegrityError):
        async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
            await unidade.sessao.execute(
                text("UPDATE estoque_pecas SET quantidade_reservada = 11 WHERE peca_id = :id"),
                {"id": peca.id},
            )


async def test_estoque_lido_para_alteracao_fica_bloqueado_ate_o_fim_da_transacao(
    fabrica_de_sessoes,
):
    """Duas OS disputando o mesmo saldo esperam uma pela outra (RNF-09)."""
    peca = await _cadastrar(fabrica_de_sessoes)

    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as primeira:
        await PostgresEstoqueRepository(primeira.sessao).buscar_por_peca(peca.id)

        with pytest.raises(DBAPIError, match="lock timeout"):
            async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as segunda:
                await segunda.sessao.execute(text("SET LOCAL lock_timeout = '200ms'"))
                await PostgresEstoqueRepository(segunda.sessao).buscar_por_peca(peca.id)
