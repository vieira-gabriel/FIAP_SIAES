from domain.entities.servico import Servico
from domain.repositories.servico_repository import ServicoRepository
from domain.value_objects.valor import Valor


class CadastrarServico:
    """O Gerente inclui um serviço no catálogo (RF-11)."""

    def __init__(self, servicos: ServicoRepository):
        self._servicos = servicos

    async def executar(
        self,
        codigo: str,
        nome: str,
        descricao: str,
        valor_base: Valor,
        tempo_estimado_minutos: int,
    ) -> Servico:
        servico = Servico(
            codigo=codigo,
            nome=nome,
            descricao=descricao,
            valor_base=valor_base,
            tempo_estimado_minutos=tempo_estimado_minutos,
        )
        await self._servicos.garantir_codigo_livre(servico)
        await self._servicos.salvar(servico)
        return servico
