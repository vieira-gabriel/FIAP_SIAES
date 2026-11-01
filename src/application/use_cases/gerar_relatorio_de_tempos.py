from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import OrdemServicoInvalida
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository


@dataclass(frozen=True)
class TempoMedio:
    periodo: str
    quantidade: int
    tempo_medio: timedelta


@dataclass(frozen=True)
class TempoMedioDoMecanico:
    periodo: str
    mecanico_id: UUID
    mecanico_nome: str | None
    quantidade: int
    tempo_medio: timedelta


@dataclass(frozen=True)
class RelatorioDeTempos:
    execucao: list[TempoMedioDoMecanico]
    espera_por_peca: list[TempoMedio]
    total: list[TempoMedio]


class GerarRelatorioDeTempos:
    """Tempos médios das OS finalizadas no período, agrupados por mês da finalização (RF-27).

    O mês é o do fuso UTC. A espera por peça tem a média só das OS que esperaram alguma peça.
    A permissão do Gerente é checada na rota.
    """

    def __init__(self, ordens: OrdemServicoRepository, usuarios: UsuarioRepository):
        self._ordens = ordens
        self._usuarios = usuarios

    async def executar(
        self, finalizadas_de: datetime | None = None, finalizadas_ate: datetime | None = None
    ) -> RelatorioDeTempos:
        _validar_periodo(finalizadas_de, finalizadas_ate)
        ordens = await self._ordens.listar_finalizadas(finalizadas_de, finalizadas_ate)
        execucao = _medias(
            ordens, lambda os: (_mes(os), os.mecanico_id), lambda os: os.tempo_de_execucao()
        )
        nomes = await self._nomes_dos_mecanicos({mecanico_id for _, mecanico_id in execucao})
        return RelatorioDeTempos(
            execucao=[
                TempoMedioDoMecanico(mes, mecanico_id, nomes.get(mecanico_id), qtd, media)
                for (mes, mecanico_id), (qtd, media) in sorted(
                    execucao.items(),
                    key=lambda item: (item[0][0], nomes.get(item[0][1], ""), str(item[0][1])),
                )
            ],
            espera_por_peca=_por_mes(
                _medias(ordens, _mes, lambda os: os.tempo_de_espera_por_peca())
            ),
            total=_por_mes(_medias(ordens, _mes, lambda os: os.tempo_total())),
        )

    async def _nomes_dos_mecanicos(self, ids: Iterable[UUID]) -> dict[UUID, str]:
        mecanicos = {id: await self._usuarios.buscar_por_id(id) for id in ids}
        return {id: mecanico.nome for id, mecanico in mecanicos.items() if mecanico is not None}


def _validar_periodo(inicio: datetime | None, fim: datetime | None) -> None:
    for momento in (inicio, fim):
        if momento is not None and momento.tzinfo is None:
            raise OrdemServicoInvalida("o período do relatório precisa ter fuso horário")
    if inicio is not None and fim is not None and inicio > fim:
        raise OrdemServicoInvalida("o início do período é posterior ao fim")


def _mes(os: OrdemServico) -> str:
    return os.data_finalizacao.astimezone(UTC).strftime("%Y-%m")


def _medias[C](
    ordens: Iterable[OrdemServico],
    chave: Callable[[OrdemServico], C],
    tempo: Callable[[OrdemServico], timedelta | None],
) -> dict[C, tuple[int, timedelta]]:
    """Quantidade e média por grupo; a OS sem o tempo (nulo) não entra no grupo."""
    tempos: dict[C, list[timedelta]] = defaultdict(list)
    for os in ordens:
        duracao = tempo(os)
        if duracao is not None:
            tempos[chave(os)].append(duracao)
    return {
        grupo: (len(duracoes), sum(duracoes, timedelta()) / len(duracoes))
        for grupo, duracoes in tempos.items()
    }


def _por_mes(medias: dict[str, tuple[int, timedelta]]) -> list[TempoMedio]:
    return [TempoMedio(mes, qtd, media) for mes, (qtd, media) in sorted(medias.items())]
