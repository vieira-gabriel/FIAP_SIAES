from uuid import UUID

from domain.entities.servico import Servico
from domain.repositories.servico_repository import ServicoRepository
from domain.value_objects.valor import Valor


class AtualizarServico:
    """O Gerente altera os dados, o valor base e o tempo estimado; as OS já orçadas não mudam,
    porque os valores foram congelados nos itens (RF-11, RF-17)."""

    def __init__(self, servicos: ServicoRepository):
        self._servicos = servicos

    async def executar(
        self,
        id: UUID,
        codigo: str,
        nome: str,
        descricao: str,
        valor_base: Valor,
        tempo_estimado_minutos: int,
    ) -> Servico:
        servico = await self._servicos.buscar_ativo_por_id(id)
        servico.atualizar_dados(codigo, nome, descricao, valor_base, tempo_estimado_minutos)
        await self._servicos.garantir_codigo_livre(servico)
        await self._servicos.salvar(servico)
        return servico
