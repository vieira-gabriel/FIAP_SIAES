from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.servico import Servico
from domain.exceptions import CodigoDeServicoJaCadastrado, EntidadeNaoEncontrada


class ServicoRepository(ABC):
    @abstractmethod
    async def salvar(self, servico: Servico) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Servico | None: ...

    @abstractmethod
    async def buscar_por_codigo(self, codigo: str) -> Servico | None:
        """Também encontra o serviço excluído, porque o código continua reservado a ele."""

    @abstractmethod
    async def listar(self) -> list[Servico]:
        """Só os serviços ativos, em ordem de nome (RF-10)."""

    async def buscar_ativo_por_id(self, id: UUID) -> Servico:
        """Para o catálogo, o serviço excluído deixa de existir; as OS dele continuam (RF-11)."""
        servico = await self.buscar_por_id(id)
        if servico is None or not servico.ativo:
            raise EntidadeNaoEncontrada("Serviço", id)
        return servico

    async def garantir_codigo_livre(self, servico: Servico) -> None:
        dono_do_codigo = await self.buscar_por_codigo(servico.codigo)
        if dono_do_codigo is not None and dono_do_codigo != servico:
            raise CodigoDeServicoJaCadastrado(servico.codigo)
