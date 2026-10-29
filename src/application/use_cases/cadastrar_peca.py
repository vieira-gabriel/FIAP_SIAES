from domain.entities.estoque_peca import EstoquePeca
from domain.entities.peca import Peca
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.peca_repository import PecaRepository
from domain.value_objects.valor import Valor


class CadastrarPeca:
    """O Gerente inclui uma peça, que nasce com o estoque na mesma transação (RF-12, RNF-08).

    A quantidade inicial não emite `SaldoPecaAtualizadoEvent`: nenhuma OS pode estar à espera
    de uma peça que acabou de ser cadastrada.
    """

    def __init__(self, pecas: PecaRepository, estoques: EstoqueRepository):
        self._pecas = pecas
        self._estoques = estoques

    async def executar(
        self,
        codigo_referencia: str,
        nome: str,
        preco_unitario: Valor,
        prazo_reposicao_dias: int,
        quantidade_fisica_inicial: int = 0,
    ) -> tuple[Peca, EstoquePeca]:
        peca = Peca(
            codigo_referencia=codigo_referencia,
            nome=nome,
            preco_unitario=preco_unitario,
            prazo_reposicao_dias=prazo_reposicao_dias,
        )
        estoque = EstoquePeca(peca_id=peca.id, quantidade_fisica=quantidade_fisica_inicial)
        await self._pecas.garantir_codigo_livre(peca)
        await self._pecas.salvar(peca)
        await self._estoques.salvar(estoque)
        return peca, estoque
