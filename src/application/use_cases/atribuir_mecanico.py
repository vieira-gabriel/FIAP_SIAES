from uuid import UUID

from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada, OrdemServicoInvalida
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository


class AtribuirMecanico:
    """O mecânico assume a OS, ou o Gerente a atribui a um mecânico, e ela passa a
    `EM_DIAGNOSTICO` (RF-16). As regras de quem pode atribuir ficam na `OrdemServico`."""

    def __init__(self, ordens: OrdemServicoRepository, usuarios: UsuarioRepository):
        self._ordens = ordens
        self._usuarios = usuarios

    async def executar(
        self, os_id: UUID, mecanico_id: UUID | None, responsavel_id: UUID
    ) -> OrdemServico:
        if mecanico_id is None:
            raise OrdemServicoInvalida("o mecânico é obrigatório")
        os = await self._ordens.buscar_por_id(os_id)
        if os is None:
            raise EntidadeNaoEncontrada("Ordem de serviço", os_id)
        responsavel = await self._usuarios.buscar_existente_por_id(responsavel_id)
        mecanico = await self._usuarios.buscar_existente_por_id(mecanico_id)
        os.atribuir_mecanico(mecanico, responsavel)
        await self._ordens.salvar(os)
        return os
