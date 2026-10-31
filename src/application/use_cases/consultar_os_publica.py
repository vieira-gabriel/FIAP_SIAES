from dataclasses import dataclass
from datetime import datetime

from application.use_cases.localizar_os_do_titular import LocalizarOSDoTitular
from domain.entities.ordem_servico import OrdemServico


@dataclass(frozen=True)
class AcompanhamentoDaOS:
    os: OrdemServico
    estimativa_entrega: datetime | None


class ConsultarOSPublica:
    """O cliente consulta a própria OS pelo número e pelo CPF/CNPJ do titular, sem login (RF-25)."""

    def __init__(self, localizar: LocalizarOSDoTitular):
        self._localizar = localizar

    async def executar(
        self, numero: str, documento: str, momento_consulta: datetime
    ) -> AcompanhamentoDaOS:
        os = await self._localizar.executar(numero, documento)
        return AcompanhamentoDaOS(os=os, estimativa_entrega=os.estimar_entrega(momento_consulta))
