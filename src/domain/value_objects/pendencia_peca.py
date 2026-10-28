from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.exceptions import AlocacaoInvalida, QuantidadeInvalida


@dataclass(frozen=True)
class PendenciaPeca:
    """Quantidade de uma peça que uma OS ainda espera receber (RF-18, RF-19).

    A data de abertura da OS define a prioridade: a mais antiga é atendida primeiro. Exige fuso
    horário, porque datas com e sem fuso não podem ser comparadas.
    """

    os_id: UUID
    data_abertura_os: datetime
    quantidade_pendente: int

    def __post_init__(self):
        if not isinstance(self.os_id, UUID):
            raise AlocacaoInvalida("a OS da pendência é obrigatória")
        if not isinstance(self.data_abertura_os, datetime) or self.data_abertura_os.tzinfo is None:
            raise AlocacaoInvalida("a data de abertura da OS deve ter fuso horário")
        if type(self.quantidade_pendente) is not int or self.quantidade_pendente <= 0:
            raise QuantidadeInvalida("deve ser um número inteiro maior que zero")
