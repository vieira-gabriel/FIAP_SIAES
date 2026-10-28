from uuid import UUID

from domain.entities.estoque_peca import EstoquePeca
from domain.entities.peca import Peca
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.peca_repository import PecaRepository
from domain.value_objects.valor import Valor


class AtualizarPeca:
    """O Gerente altera os dados cadastrais; as OS já orçadas não mudam, porque o preço e o
    prazo de reposição foram congelados nos itens (RF-12, RF-17)."""

    def __init__(self, pecas: PecaRepository, estoques: EstoqueRepository):
        self._pecas = pecas
        self._estoques = estoques

    async def executar(
        self,
        id: UUID,
        codigo_referencia: str,
        nome: str,
        preco_unitario: Valor,
        prazo_reposicao_dias: int,
    ) -> tuple[Peca, EstoquePeca]:
        peca = await self._pecas.buscar_ativa_por_id(id)
        peca.atualizar_dados(codigo_referencia, nome, preco_unitario, prazo_reposicao_dias)
        await self._pecas.garantir_codigo_livre(peca)
        await self._pecas.salvar(peca)
        estoques = await self._estoques.buscar_por_pecas([peca.id])
        return peca, estoques[peca.id]
