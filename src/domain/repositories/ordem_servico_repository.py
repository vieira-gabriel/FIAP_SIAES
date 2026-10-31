from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.value_objects.filtro_ordens_servico import FiltroOrdensServico
from domain.value_objects.numero_os import NumeroOS


class OrdemServicoRepository(ABC):
    @abstractmethod
    async def salvar(self, os: OrdemServico) -> None:
        """Os registros do histórico já gravados nunca são alterados nem removidos (RF-24)."""

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> OrdemServico | None: ...

    @abstractmethod
    async def buscar_por_numero(self, numero: NumeroOS) -> OrdemServico | None: ...

    @abstractmethod
    async def listar(self, filtro: FiltroOrdensServico) -> list[OrdemServico]:
        """As OS que atendem a todos os critérios do filtro, das abertas mais recentemente às
        mais antigas (RF-14)."""

    @abstractmethod
    async def listar_pendentes_da_peca(self, peca_id: UUID) -> list[OrdemServico]:
        """As OS com quantidade pendente da peça, da abertura mais antiga à mais nova (RF-19).

        Não filtra por status: a rejeição e o cancelamento já descartam as pendências. Não
        bloqueia as OS: quem chama bloqueia antes o estoque da peça, e quem for alterar uma OS da
        lista a relê com `buscar_por_id`, que a bloqueia. Bloquear as OS aqui, depois do estoque,
        inverteria a ordem do cancelamento (OS e depois estoque) e causaria impasse.
        """
