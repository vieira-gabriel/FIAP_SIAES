from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.peca import Peca
from domain.exceptions import CodigoDePecaJaCadastrado
from domain.repositories.peca_repository import PecaRepository
from domain.value_objects.valor import Valor
from infrastructure.database.peca_model import PecaModel

_RESTRICAO_DO_CODIGO = "pecas_codigo_referencia_key"


class PostgresPecaRepository(PecaRepository):
    """Usa a sessão da unidade de trabalho; quem confirma a transação é ela (RNF-08)."""

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, peca: Peca) -> None:
        # `garantir_codigo_livre` consulta antes de gravar, e dois cadastros simultâneos com o
        # mesmo código passam pela consulta. O `flush` leva a gravação ao banco aqui, para a
        # restrição única virar a exceção do domínio (422) em vez de erro 500 no commit.
        await self._sessao.merge(_para_modelo(peca))
        try:
            await self._sessao.flush()
        except IntegrityError as erro:
            if _RESTRICAO_DO_CODIGO not in str(erro.orig):
                raise
            raise CodigoDePecaJaCadastrado(peca.codigo_referencia) from erro

    async def buscar_por_id(self, id: UUID) -> Peca | None:
        modelo = await self._sessao.get(PecaModel, id)
        return _para_entidade(modelo) if modelo else None

    async def buscar_por_codigo_referencia(self, codigo_referencia: str) -> Peca | None:
        consulta = select(PecaModel).where(PecaModel.codigo_referencia == codigo_referencia)
        modelo = await self._sessao.scalar(consulta)
        return _para_entidade(modelo) if modelo else None

    async def listar(self) -> list[Peca]:
        consulta = (
            select(PecaModel)
            .where(PecaModel.ativo.is_(True))
            .order_by(PecaModel.nome, PecaModel.id)
        )
        return [_para_entidade(modelo) for modelo in await self._sessao.scalars(consulta)]


def _para_modelo(peca: Peca) -> PecaModel:
    return PecaModel(
        id=peca.id,
        codigo_referencia=peca.codigo_referencia,
        nome=peca.nome,
        preco_unitario=peca.preco_unitario.valor,
        prazo_reposicao_dias=peca.prazo_reposicao_dias,
        ativo=peca.ativo,
    )


def _para_entidade(modelo: PecaModel) -> Peca:
    return Peca(
        id=modelo.id,
        codigo_referencia=modelo.codigo_referencia,
        nome=modelo.nome,
        preco_unitario=Valor(modelo.preco_unitario),
        prazo_reposicao_dias=modelo.prazo_reposicao_dias,
        ativo=modelo.ativo,
    )
