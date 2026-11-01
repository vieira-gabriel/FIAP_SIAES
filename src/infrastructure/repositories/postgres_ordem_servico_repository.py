from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Select, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.item_peca import ItemPeca
from domain.entities.item_servico import ItemServico
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import NumeroOSJaCadastrado
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.value_objects.filtro_ordens_servico import FiltroOrdensServico
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.orcamento import Orcamento
from domain.value_objects.valor import Valor
from infrastructure.database.ordem_servico_model import (
    HistoricoStatusOSModel,
    ItemPecaModel,
    ItemServicoModel,
    OrdemServicoModel,
)

_RESTRICAO_DO_NUMERO = "ordens_servico_numero_key"


class PostgresOrdemServicoRepository(OrdemServicoRepository):
    """Usa a sessão da unidade de trabalho; quem confirma a transação é ela (RNF-08).

    As buscas de uma OS bloqueiam a OS lida até o fim da transação: duas operações na mesma OS
    esperam uma pela outra, e a segunda parte do status e do histórico gravados pela primeira
    (RNF-09). A lista de pendências não bloqueia, porque quem a usa já bloqueou o estoque da peça.
    """

    def __init__(self, sessao: AsyncSession):
        self._sessao = sessao

    async def salvar(self, os: OrdemServico) -> None:
        # O `flush` leva a gravação ao banco aqui, para a restrição única do número virar a
        # exceção do domínio (422) em vez de erro 500 no commit, e para a OS existir antes da
        # inserção do histórico.
        await self._sessao.merge(_para_modelo(os))
        try:
            await self._sessao.flush()
        except IntegrityError as erro:
            if _RESTRICAO_DO_NUMERO not in str(erro.orig):
                raise
            raise NumeroOSJaCadastrado(os.numero.valor) from erro
        await self._inserir_historico_novo(os)

    async def buscar_por_id(self, id: UUID) -> OrdemServico | None:
        modelo = await self._sessao.scalar(
            _consulta_com_bloqueio().where(OrdemServicoModel.id == id)
        )
        return _para_entidade(modelo) if modelo else None

    async def buscar_por_numero(self, numero: NumeroOS) -> OrdemServico | None:
        consulta = _consulta_com_bloqueio().where(OrdemServicoModel.numero == numero.valor)
        modelo = await self._sessao.scalar(consulta)
        return _para_entidade(modelo) if modelo else None

    async def listar(self, filtro: FiltroOrdensServico) -> list[OrdemServico]:
        consulta = (
            _consulta()
            .where(*_condicoes(filtro))
            .order_by(OrdemServicoModel.data_abertura.desc(), OrdemServicoModel.id)
        )
        return [_para_entidade(modelo) for modelo in await self._sessao.scalars(consulta)]

    async def listar_finalizadas(
        self, finalizadas_de: datetime | None, finalizadas_ate: datetime | None
    ) -> list[OrdemServico]:
        condicoes = [OrdemServicoModel.data_finalizacao.is_not(None)]
        if finalizadas_de is not None:
            condicoes.append(OrdemServicoModel.data_finalizacao >= finalizadas_de)
        if finalizadas_ate is not None:
            condicoes.append(OrdemServicoModel.data_finalizacao <= finalizadas_ate)
        consulta = (
            _consulta()
            .where(*condicoes)
            .order_by(OrdemServicoModel.data_finalizacao, OrdemServicoModel.id)
        )
        return [_para_entidade(modelo) for modelo in await self._sessao.scalars(consulta)]

    async def listar_pendentes_da_peca(self, peca_id: UUID) -> list[OrdemServico]:
        com_pendencia = exists().where(
            ItemPecaModel.os_id == OrdemServicoModel.id,
            ItemPecaModel.peca_id == peca_id,
            ItemPecaModel.quantidade_pendente > 0,
        )
        consulta = (
            _consulta()
            .where(com_pendencia)
            .order_by(OrdemServicoModel.data_abertura, OrdemServicoModel.id)
        )
        return [_para_entidade(modelo) for modelo in await self._sessao.scalars(consulta)]

    async def _inserir_historico_novo(self, os: OrdemServico) -> None:
        """Só insere: um registro já gravado nunca é atualizado nem removido (RF-24)."""
        gravados = set(
            await self._sessao.scalars(
                select(HistoricoStatusOSModel.id).where(HistoricoStatusOSModel.os_id == os.id)
            )
        )
        novos = [registro for registro in os.historico if registro.id not in gravados]
        self._sessao.add_all(_para_modelo_de_historico(os.id, registro) for registro in novos)
        await self._sessao.flush()


def _consulta() -> Select[tuple[OrdemServicoModel]]:
    # `populate_existing` relê a OS mesmo que a sessão já a tenha carregado: depois de um
    # bloqueio, o estado usado é o gravado pela transação que o liberou.
    return (
        select(OrdemServicoModel)
        .options(
            selectinload(OrdemServicoModel.servicos),
            selectinload(OrdemServicoModel.pecas),
            selectinload(OrdemServicoModel.historico),
        )
        .execution_options(populate_existing=True)
    )


def _consulta_com_bloqueio() -> Select[tuple[OrdemServicoModel]]:
    # Só a linha da OS é bloqueada; os itens e o histórico só mudam junto com ela.
    return _consulta().with_for_update(of=OrdemServicoModel)


def _condicoes(filtro: FiltroOrdensServico) -> list[ColumnElement[bool]]:
    condicoes: list[ColumnElement[bool]] = []
    if filtro.status is not None:
        condicoes.append(OrdemServicoModel.status == filtro.status)
    if filtro.mecanico_id is not None:
        condicoes.append(OrdemServicoModel.mecanico_id == filtro.mecanico_id)
    if filtro.cliente_id is not None:
        condicoes.append(OrdemServicoModel.cliente_id == filtro.cliente_id)
    if filtro.veiculos_ids is not None:
        condicoes.append(OrdemServicoModel.veiculo_id.in_(filtro.veiculos_ids))
    if filtro.abertura_de is not None:
        condicoes.append(OrdemServicoModel.data_abertura >= filtro.abertura_de)
    if filtro.abertura_ate is not None:
        condicoes.append(OrdemServicoModel.data_abertura <= filtro.abertura_ate)
    return condicoes


def _para_modelo(os: OrdemServico) -> OrdemServicoModel:
    return OrdemServicoModel(
        id=os.id,
        numero=os.numero.valor,
        cliente_id=os.cliente_id,
        veiculo_id=os.veiculo_id,
        atendente_id=os.atendente_id,
        mecanico_id=os.mecanico_id,
        status=os.status,
        data_abertura=os.data_abertura,
        data_inicio_execucao=os.data_inicio_execucao,
        data_finalizacao=os.data_finalizacao,
        subtotal_servicos=os.orcamento.subtotal_servicos.valor if os.orcamento else None,
        subtotal_pecas=os.orcamento.subtotal_pecas.valor if os.orcamento else None,
        servicos=[
            ItemServicoModel(
                os_id=os.id,
                servico_id=item.servico_id,
                nome=item.nome,
                preco_congelado=item.preco_congelado.valor,
                tempo_estimado_minutos=item.tempo_estimado_minutos,
            )
            for item in os.servicos
        ],
        pecas=[
            ItemPecaModel(
                os_id=os.id,
                peca_id=item.peca_id,
                nome=item.nome,
                quantidade=item.quantidade,
                preco_unitario_congelado=item.preco_unitario_congelado.valor,
                prazo_reposicao_dias=item.prazo_reposicao_dias,
                quantidade_reservada=item.quantidade_reservada,
                quantidade_pendente=item.quantidade_pendente,
            )
            for item in os.pecas
        ],
    )


def _para_modelo_de_historico(os_id: UUID, registro: HistoricoStatusOS) -> HistoricoStatusOSModel:
    return HistoricoStatusOSModel(
        id=registro.id,
        os_id=os_id,
        status_anterior=registro.status_anterior,
        status_novo=registro.status_novo,
        data_hora=registro.data_hora,
        origem=registro.origem,
        usuario_id=registro.usuario_id,
        motivo=registro.motivo,
    )


def _para_entidade(modelo: OrdemServicoModel) -> OrdemServico:
    orcamento = (
        Orcamento(
            subtotal_servicos=Valor(modelo.subtotal_servicos),
            subtotal_pecas=Valor(modelo.subtotal_pecas),
        )
        if modelo.subtotal_servicos is not None
        else None
    )
    return OrdemServico(
        id=modelo.id,
        numero=NumeroOS(modelo.numero),
        cliente_id=modelo.cliente_id,
        veiculo_id=modelo.veiculo_id,
        atendente_id=modelo.atendente_id,
        mecanico_id=modelo.mecanico_id,
        status=modelo.status,
        data_abertura=modelo.data_abertura,
        data_inicio_execucao=modelo.data_inicio_execucao,
        data_finalizacao=modelo.data_finalizacao,
        servicos=[
            ItemServico(
                servico_id=item.servico_id,
                nome=item.nome,
                preco_congelado=Valor(item.preco_congelado),
                tempo_estimado_minutos=item.tempo_estimado_minutos,
            )
            for item in sorted(modelo.servicos, key=lambda item: item.nome)
        ],
        pecas=[
            ItemPeca(
                peca_id=item.peca_id,
                nome=item.nome,
                quantidade=item.quantidade,
                preco_unitario_congelado=Valor(item.preco_unitario_congelado),
                prazo_reposicao_dias=item.prazo_reposicao_dias,
                quantidade_reservada=item.quantidade_reservada,
                quantidade_pendente=item.quantidade_pendente,
            )
            for item in sorted(modelo.pecas, key=lambda item: item.nome)
        ],
        orcamento=orcamento,
        historico=_em_ordem(
            HistoricoStatusOS(
                id=registro.id,
                status_anterior=registro.status_anterior,
                status_novo=registro.status_novo,
                data_hora=registro.data_hora,
                origem=registro.origem,
                usuario_id=registro.usuario_id,
                motivo=registro.motivo,
            )
            for registro in modelo.historico
        ),
    )


def _em_ordem(registros: Iterable[HistoricoStatusOS]) -> tuple[HistoricoStatusOS, ...]:
    """Ordena por data e hora; no mesmo instante, o registro que parte do status deixado pelo
    anterior vem antes, porque duas transições na mesma transação podem ter o mesmo horário."""
    restantes = sorted(registros, key=lambda registro: registro.data_hora)
    ordenados: list[HistoricoStatusOS] = []
    while restantes:
        status_atual = ordenados[-1].status_novo if ordenados else None
        empatados = [r for r in restantes if r.data_hora == restantes[0].data_hora]
        seguinte = next((r for r in empatados if r.status_anterior == status_atual), empatados[0])
        ordenados.append(seguinte)
        restantes.remove(seguinte)
    return tuple(ordenados)
