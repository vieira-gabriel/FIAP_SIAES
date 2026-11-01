from uuid import UUID

from pydantic import BaseModel, Field

from application.use_cases.gerar_relatorio_de_tempos import (
    RelatorioDeTempos,
    TempoMedio,
    TempoMedioDoMecanico,
)


class TempoMedioResponse(BaseModel):
    periodo: str = Field(description="Mês da finalização das OS, no formato AAAA-MM (UTC).")
    quantidade_os: int = Field(description="OS que entraram na média.")
    tempo_medio_segundos: float

    @classmethod
    def de_tempo_medio(cls, tempo: TempoMedio) -> "TempoMedioResponse":
        return cls(
            periodo=tempo.periodo,
            quantidade_os=tempo.quantidade,
            tempo_medio_segundos=tempo.tempo_medio.total_seconds(),
        )


class TempoMedioDoMecanicoResponse(TempoMedioResponse):
    mecanico_id: UUID
    mecanico_nome: str | None

    @classmethod
    def de_tempo_do_mecanico(cls, tempo: TempoMedioDoMecanico) -> "TempoMedioDoMecanicoResponse":
        return cls(
            periodo=tempo.periodo,
            quantidade_os=tempo.quantidade,
            tempo_medio_segundos=tempo.tempo_medio.total_seconds(),
            mecanico_id=tempo.mecanico_id,
            mecanico_nome=tempo.mecanico_nome,
        )


class RelatorioDeTemposResponse(BaseModel):
    execucao: list[TempoMedioDoMecanicoResponse] = Field(
        description="Tempo médio de execução por mês e por mecânico responsável."
    )
    espera_por_peca: list[TempoMedioResponse] = Field(
        description="Tempo médio de espera por peça por mês, só das OS que esperaram."
    )
    total: list[TempoMedioResponse] = Field(
        description="Tempo médio da abertura à finalização por mês."
    )

    @classmethod
    def de_relatorio(cls, relatorio: RelatorioDeTempos) -> "RelatorioDeTemposResponse":
        return cls(
            execucao=[
                TempoMedioDoMecanicoResponse.de_tempo_do_mecanico(t) for t in relatorio.execucao
            ],
            espera_por_peca=[
                TempoMedioResponse.de_tempo_medio(t) for t in relatorio.espera_por_peca
            ],
            total=[TempoMedioResponse.de_tempo_medio(t) for t in relatorio.total],
        )
