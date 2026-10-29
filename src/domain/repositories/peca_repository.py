from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.peca import Peca
from domain.exceptions import CodigoDePecaJaCadastrado, EntidadeNaoEncontrada


class PecaRepository(ABC):
    @abstractmethod
    async def salvar(self, peca: Peca) -> None: ...

    @abstractmethod
    async def buscar_por_id(self, id: UUID) -> Peca | None: ...

    @abstractmethod
    async def buscar_por_codigo_referencia(self, codigo_referencia: str) -> Peca | None:
        """Também encontra a peça excluída, porque o código continua reservado a ela."""

    @abstractmethod
    async def listar(self) -> list[Peca]:
        """Só as peças ativas, em ordem de nome (RF-12)."""

    async def buscar_ativa_por_id(self, id: UUID) -> Peca:
        """Para o cadastro, a peça excluída deixa de existir; as reservas dela continuam (RF-12)."""
        peca = await self.buscar_por_id(id)
        if peca is None or not peca.ativo:
            raise EntidadeNaoEncontrada("Peça", id)
        return peca

    async def garantir_codigo_livre(self, peca: Peca) -> None:
        dono_do_codigo = await self.buscar_por_codigo_referencia(peca.codigo_referencia)
        if dono_do_codigo is not None and dono_do_codigo != peca:
            raise CodigoDePecaJaCadastrado(peca.codigo_referencia)
