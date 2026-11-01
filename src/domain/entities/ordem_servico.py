from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from domain.entities.historico_status_os import HistoricoStatusOS
from domain.entities.item_peca import ItemPeca
from domain.entities.item_servico import ItemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.entities.usuario import Usuario
from domain.events.domain_event import DomainEvent
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.exceptions import (
    AcessoNegado,
    EntidadeNaoEncontrada,
    ItemIndisponivel,
    ItemJaIncluido,
    ItensBloqueados,
    MecanicoIndisponivel,
    MotivoInvalido,
    MotivoObrigatorio,
    OrdemServicoInvalida,
    PecasPendentes,
    TransicaoDeStatusInvalida,
)
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.orcamento import Orcamento
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.quantidade_peca import QuantidadePeca
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

_CANCELAVEIS = frozenset(StatusOS) - {StatusOS.FINALIZADA, StatusOS.ENTREGUE, StatusOS.CANCELADA}


@dataclass(eq=False)
class OrdemServico:
    """Raiz do agregado principal: o atendimento de um veículo, da abertura à entrega (RF-13).

    Os itens só mudam durante o diagnóstico e só aceitam serviços e peças ativos (RF-17). O
    orçamento soma os valores congelados nos itens (RNF-11). Apenas as transições da Linguagem
    Ubíqua (§5) são permitidas, cada uma por um método que declara de quais status parte, e
    cada transição gera um registro no histórico (RF-24). A conclusão do orçamento, o
    cancelamento e o início da execução acumulam um evento de domínio para o estoque reagir
    (RF-18, RF-20, RF-23).
    """

    numero: NumeroOS
    cliente_id: UUID
    veiculo_id: UUID
    atendente_id: UUID
    mecanico_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    status: StatusOS = StatusOS.RECEBIDA
    data_abertura: datetime = field(default_factory=lambda: datetime.now(UTC))
    data_inicio_execucao: datetime | None = None
    data_finalizacao: datetime | None = None
    servicos: list[ItemServico] = field(default_factory=list)
    pecas: list[ItemPeca] = field(default_factory=list)
    orcamento: Orcamento | None = None
    historico: tuple[HistoricoStatusOS, ...] = ()
    _domain_events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.numero, NumeroOS):
            raise OrdemServicoInvalida("o número da OS é obrigatório")
        for nome, identificador in (
            ("a OS", self.id),
            ("o cliente", self.cliente_id),
            ("o veículo", self.veiculo_id),
            ("o atendente", self.atendente_id),
        ):
            if not isinstance(identificador, UUID):
                raise OrdemServicoInvalida(f"{nome} é obrigatório")
        if not isinstance(self.status, StatusOS):
            raise OrdemServicoInvalida("o status da OS é inválido")
        if not isinstance(self.data_abertura, datetime) or self.data_abertura.tzinfo is None:
            raise OrdemServicoInvalida("a data de abertura da OS deve ter fuso horário")
        self._validar_historico()

    def __setattr__(self, nome: str, valor: object) -> None:
        # RF-24: os registros do histórico não podem ser alterados nem removidos, então o
        # histórico só muda pelas transições, e nunca por uma atribuição feita de fora.
        if nome == "historico" and "historico" in self.__dict__:
            raise AttributeError("o histórico da OS só muda pelas transições de status")
        super().__setattr__(nome, valor)

    @classmethod
    def abrir(
        cls,
        *,
        numero: NumeroOS,
        cliente_id: UUID,
        veiculo_id: UUID,
        atendente_id: UUID,
        id: UUID | None = None,
    ) -> "OrdemServico":
        """Abre uma OS nova em `RECEBIDA` e registra a abertura no histórico (RF-13, RF-24).

        É o único ponto que cria o registro de abertura: o construtor só reconstitui uma OS, e
        por isso nunca inventa um registro que a persistência já guarda.
        """
        os = cls(
            numero=numero,
            cliente_id=cliente_id,
            veiculo_id=veiculo_id,
            atendente_id=atendente_id,
            id=id if id is not None else uuid4(),
        )
        os._acrescentar_ao_historico(
            HistoricoStatusOS(
                status_anterior=None,
                status_novo=StatusOS.RECEBIDA,
                data_hora=os.data_abertura,
                origem=OrigemTransicao.USUARIO,
                usuario_id=atendente_id,
            )
        )
        return os

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, OrdemServico) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def incluir_servico(self, servico: Servico) -> None:
        self._exigir_itens_editaveis()
        if not servico.pode_ser_incluido_em_os():
            raise ItemIndisponivel(servico.nome)
        if any(item.servico_id == servico.id for item in self.servicos):
            raise ItemJaIncluido(servico.nome)
        self.servicos.append(ItemServico.a_partir_de(servico))
        self.orcamento = None

    def incluir_peca(self, peca: Peca, quantidade: int) -> None:
        self._exigir_itens_editaveis()
        if not peca.pode_ser_incluida_em_os():
            raise ItemIndisponivel(peca.nome)
        if any(item.peca_id == peca.id for item in self.pecas):
            raise ItemJaIncluido(peca.nome)
        self.pecas.append(ItemPeca.a_partir_de(peca, quantidade))
        self.orcamento = None

    def remover_servico(self, servico_id: UUID) -> None:
        self._exigir_itens_editaveis()
        item = next((item for item in self.servicos if item.servico_id == servico_id), None)
        if item is None:
            raise EntidadeNaoEncontrada("Item de serviço", servico_id)
        self.servicos.remove(item)
        self.orcamento = None

    def remover_peca(self, peca_id: UUID) -> None:
        self._exigir_itens_editaveis()
        self.pecas.remove(self._item_da_peca(peca_id))
        self.orcamento = None

    def alocar_peca(self, peca_id: UUID, quantidade: int) -> None:
        """Converte a quantidade pendente da peça em reservada e libera a OS sem pendências.

        Só a OS em `AGUARDANDO_PECA` é liberada. Em `AGUARDANDO_APROVACAO` a reserva não muda o
        status, e o cliente ainda decide sobre o orçamento (RF-18, RF-19).
        """
        self._item_da_peca(peca_id).alocar(quantidade)
        if self.status is StatusOS.AGUARDANDO_PECA and not self._nomes_das_pecas_pendentes():
            self.liberar_para_execucao()

    def congelar_valores(
        self, servicos_vigentes: Iterable[Servico], pecas_vigentes: Iterable[Peca]
    ) -> None:
        """Atualiza os itens com os valores vigentes do catálogo e calcula o orçamento (RF-17).

        O domínio não consulta o catálogo: o caso de uso entrega o `Servico` e a `Peca` de cada
        item. Se faltar algum, ou se algum foi excluído do catálogo depois de incluído, nenhum item
        é alterado. O orçamento vale até os itens mudarem:
        incluir ou remover um item o descarta, e só então o congelamento pode ser refeito.
        """
        self._exigir_itens_editaveis()
        servicos = {servico.id: servico for servico in servicos_vigentes}
        pecas = {peca.id: peca for peca in pecas_vigentes}
        sem_valor_vigente = [i.nome for i in self.servicos if i.servico_id not in servicos]
        sem_valor_vigente += [i.nome for i in self.pecas if i.peca_id not in pecas]
        if sem_valor_vigente:
            raise OrdemServicoInvalida(
                f"faltam os valores vigentes de: {', '.join(sem_valor_vigente)}"
            )
        excluidos = [
            i.nome for i in self.servicos if not servicos[i.servico_id].pode_ser_incluido_em_os()
        ]
        excluidos += [i.nome for i in self.pecas if not pecas[i.peca_id].pode_ser_incluida_em_os()]
        if excluidos:
            raise ItemIndisponivel(excluidos[0])
        for item_servico in self.servicos:
            item_servico.congelar(servicos[item_servico.servico_id])
        for item_peca in self.pecas:
            item_peca.congelar(pecas[item_peca.peca_id])
        self.orcamento = Orcamento(
            subtotal_servicos=_somar(item.preco_congelado for item in self.servicos),
            subtotal_pecas=_somar(item.valor_total() for item in self.pecas),
        )

    def atribuir_mecanico(self, mecanico: Usuario, responsavel: Usuario) -> None:
        """O mecânico assume a OS, que passa a `EM_DIAGNOSTICO` (RF-16).

        O Mecânico só atribui a OS a si mesmo, e o Gerente a qualquer mecânico ativo. O histórico
        grava o responsável, que é quem executa a transição (RF-24).
        """
        for usuario in (mecanico, responsavel):
            if not isinstance(usuario, Usuario):
                raise OrdemServicoInvalida("o mecânico e o responsável são obrigatórios")
        self._validar_transicao(StatusOS.EM_DIAGNOSTICO, de={StatusOS.RECEBIDA})
        if not responsavel.ativo:
            raise AcessoNegado("Usuário desativado não pode atribuir o mecânico.")
        assume_a_propria_os = (
            responsavel.perfil == PerfilUsuario.MECANICO and responsavel == mecanico
        )
        if responsavel.perfil != PerfilUsuario.GERENTE and not assume_a_propria_os:
            raise AcessoNegado("O mecânico só atribui a OS a si mesmo, e o Gerente a qualquer um.")
        if not (mecanico.ativo and mecanico.perfil == PerfilUsuario.MECANICO):
            raise MecanicoIndisponivel()
        self._mudar_status(
            StatusOS.EM_DIAGNOSTICO,
            de={StatusOS.RECEBIDA},
            origem=OrigemTransicao.USUARIO,
            usuario_id=responsavel.id,
        )
        self.mecanico_id = mecanico.id

    def finalizar_orcamento(
        self,
        usuario_id: UUID,
        servicos_vigentes: Iterable[Servico],
        pecas_vigentes: Iterable[Peca],
    ) -> None:
        """Congela os valores vigentes e envia o orçamento ao cliente (RF-17).

        A quantidade de cada peça fica toda pendente, até a reserva de estoque (RF-18).
        """
        _exigir_usuario(usuario_id)
        self._validar_transicao(StatusOS.AGUARDANDO_APROVACAO, de={StatusOS.EM_DIAGNOSTICO})
        self.congelar_valores(servicos_vigentes, pecas_vigentes)
        for item in self.pecas:
            item.marcar_como_pendente()
        self._mudar_status(
            StatusOS.AGUARDANDO_APROVACAO,
            de={StatusOS.EM_DIAGNOSTICO},
            origem=OrigemTransicao.USUARIO,
            usuario_id=usuario_id,
        )
        self._domain_events.append(OrcamentoFinalizadoEvent(os_id=self.id))

    def aprovar_orcamento(self) -> None:
        """Com peças pendentes a OS espera a reposição; sem elas, aguarda a execução (RF-26)."""
        destino = (
            StatusOS.AGUARDANDO_PECA
            if self._nomes_das_pecas_pendentes()
            else StatusOS.AGUARDANDO_EXECUCAO
        )
        self._mudar_status(
            destino, de={StatusOS.AGUARDANDO_APROVACAO}, origem=OrigemTransicao.CLIENTE
        )

    def rejeitar_orcamento(self) -> None:
        """Cancela a OS e descarta as pendências; as reservadas voltam ao estoque pelo estorno."""
        self._mudar_status(
            StatusOS.CANCELADA, de={StatusOS.AGUARDANDO_APROVACAO}, origem=OrigemTransicao.CLIENTE
        )
        self._descartar_pendencias()
        self._acumular_os_cancelada(baixa_ja_realizada=False)

    def liberar_para_execucao(self) -> None:
        """A OS só sai de `AGUARDANDO_PECA` quando todas as peças estão reservadas (RF-19)."""
        self._validar_transicao(StatusOS.AGUARDANDO_EXECUCAO, de={StatusOS.AGUARDANDO_PECA})
        if pendentes := self._nomes_das_pecas_pendentes():
            raise PecasPendentes(pendentes)
        self._mudar_status(
            StatusOS.AGUARDANDO_EXECUCAO,
            de={StatusOS.AGUARDANDO_PECA},
            origem=OrigemTransicao.SISTEMA,
        )

    def iniciar_execucao(self, usuario: Usuario) -> None:
        """Só o mecânico atribuído ou o Gerente, e ativos, iniciam; grava o início (RF-20)."""
        if not isinstance(usuario, Usuario):
            raise OrdemServicoInvalida("o usuário é obrigatório")
        self._validar_transicao(StatusOS.EM_EXECUCAO, de={StatusOS.AGUARDANDO_EXECUCAO})
        self._exigir_mecanico_atribuido_ou_gerente(usuario, "iniciar a execução")
        self.data_inicio_execucao = self._mudar_status(
            StatusOS.EM_EXECUCAO,
            de={StatusOS.AGUARDANDO_EXECUCAO},
            origem=OrigemTransicao.USUARIO,
            usuario_id=usuario.id,
        )
        self._domain_events.append(
            ExecucaoIniciadaEvent(os_id=self.id, baixas=self._quantidades_reservadas())
        )

    def cancelar(self, usuario_id: UUID, motivo: str) -> None:
        """Vale de `RECEBIDA` até `EM_EXECUCAO` e exige o motivo, que vai ao histórico (RF-23).

        Descarta as pendências dos itens (RF-18).
        """
        _exigir_usuario(usuario_id)
        self._validar_transicao(StatusOS.CANCELADA, de=_CANCELAVEIS)
        if not isinstance(motivo, str) or not motivo.strip():
            raise MotivoObrigatorio()
        if "<" in motivo:
            raise MotivoInvalido()
        baixa_ja_realizada = self.status is StatusOS.EM_EXECUCAO
        self._mudar_status(
            StatusOS.CANCELADA,
            de=_CANCELAVEIS,
            origem=OrigemTransicao.USUARIO,
            usuario_id=usuario_id,
            motivo=motivo,
        )
        self._descartar_pendencias()
        self._acumular_os_cancelada(baixa_ja_realizada=baixa_ja_realizada)

    def concluir_manutencao(self, usuario: Usuario) -> None:
        """Só o mecânico atribuído ou o Gerente, e ativos, concluem; grava o momento (RF-21)."""
        if not isinstance(usuario, Usuario):
            raise OrdemServicoInvalida("o usuário é obrigatório")
        self._validar_transicao(StatusOS.FINALIZADA, de={StatusOS.EM_EXECUCAO})
        self._exigir_mecanico_atribuido_ou_gerente(usuario, "concluir a manutenção")
        self.data_finalizacao = self._mudar_status(
            StatusOS.FINALIZADA,
            de={StatusOS.EM_EXECUCAO},
            origem=OrigemTransicao.USUARIO,
            usuario_id=usuario.id,
        )

    def entregar_veiculo(self, usuario_id: UUID) -> None:
        """Entrega ao cliente após o acerto comercial, estado final (RF-22)."""
        _exigir_usuario(usuario_id)
        self._mudar_status(
            StatusOS.ENTREGUE,
            de={StatusOS.FINALIZADA},
            origem=OrigemTransicao.USUARIO,
            usuario_id=usuario_id,
        )

    def _exigir_mecanico_atribuido_ou_gerente(self, usuario: Usuario, acao: str) -> None:
        if not usuario.ativo:
            raise AcessoNegado(f"Usuário desativado não pode {acao}.")
        if usuario.perfil != PerfilUsuario.GERENTE and usuario.id != self.mecanico_id:
            raise AcessoNegado(f"Apenas o mecânico atribuído ou o Gerente pode {acao}.")

    def estimar_entrega(self, momento_consulta: datetime) -> datetime | None:
        """Data prevista de entrega pela tabela do RF-25, com os valores congelados nos itens.

        O momento da consulta vem de fora para o cálculo ser testável. O tempo é corrido, e o
        prazo das peças é o maior entre as que ainda estão pendentes.
        """
        if not isinstance(momento_consulta, datetime) or momento_consulta.tzinfo is None:
            raise OrdemServicoInvalida("o momento da consulta deve ter fuso horário")
        try:
            return self._estimativa(momento_consulta)
        except OverflowError:
            raise OrdemServicoInvalida("os prazos dos itens passam do limite de datas") from None

    def tempo_de_execucao(self) -> timedelta:
        """Do início da execução até a finalização, sem as esperas anteriores (RF-27)."""
        inicio = _registrada(self.data_inicio_execucao, "o início da execução")
        return _registrada(self.data_finalizacao, "a finalização") - inicio

    def tempo_total(self) -> timedelta:
        """Da abertura até a finalização, incluindo todas as esperas (RF-27)."""
        return _registrada(self.data_finalizacao, "a finalização") - self.data_abertura

    def tempo_de_espera_por_peca(self) -> timedelta | None:
        """Soma dos intervalos entre a entrada e a saída de `AGUARDANDO_PECA` no histórico
        (RF-27). Nulo se a OS nunca esperou peça; a espera em andamento não conta."""
        esperas = [
            saida.data_hora - entrada.data_hora
            for entrada, saida in zip(self.historico, self.historico[1:], strict=False)
            if entrada.status_novo == StatusOS.AGUARDANDO_PECA
        ]
        return sum(esperas, timedelta()) if esperas else None

    def collect_domain_events(self) -> list[DomainEvent]:
        eventos, self._domain_events = self._domain_events, []
        return eventos

    def _estimativa(self, momento_consulta: datetime) -> datetime | None:
        match self.status:
            case StatusOS.RECEBIDA | StatusOS.EM_DIAGNOSTICO | StatusOS.CANCELADA:
                return None
            case StatusOS.AGUARDANDO_APROVACAO | StatusOS.AGUARDANDO_PECA:
                return momento_consulta + self._prazo_das_pecas_pendentes() + self._duracao()
            case StatusOS.AGUARDANDO_EXECUCAO:
                return momento_consulta + self._duracao()
            case StatusOS.EM_EXECUCAO:
                inicio = _registrada(self.data_inicio_execucao, "o início da execução")
                return inicio + self._duracao()
            case StatusOS.FINALIZADA | StatusOS.ENTREGUE:
                return _registrada(self.data_finalizacao, "a finalização")

    def _duracao(self) -> timedelta:
        return timedelta(minutes=sum(item.tempo_estimado_minutos for item in self.servicos))

    def _prazo_das_pecas_pendentes(self) -> timedelta:
        prazos = [item.prazo_reposicao_dias for item in self.pecas if item.quantidade_pendente > 0]
        return timedelta(days=max(prazos, default=0))

    def _item_da_peca(self, peca_id: UUID) -> ItemPeca:
        item = next((item for item in self.pecas if item.peca_id == peca_id), None)
        if item is None:
            raise EntidadeNaoEncontrada("Item de peça", peca_id)
        return item

    def _exigir_itens_editaveis(self) -> None:
        if self.status != StatusOS.EM_DIAGNOSTICO:
            raise ItensBloqueados(self.status)

    def _descartar_pendencias(self) -> None:
        for item in self.pecas:
            item.descartar_pendencia()

    def _acumular_os_cancelada(self, *, baixa_ja_realizada: bool) -> None:
        estornos = [] if baixa_ja_realizada else self._quantidades_reservadas()
        self._domain_events.append(OSCanceladaEvent(os_id=self.id, estornos=estornos))

    def _quantidades_reservadas(self) -> list[QuantidadePeca]:
        return [
            QuantidadePeca(item.peca_id, item.quantidade_reservada)
            for item in self.pecas
            if item.quantidade_reservada > 0
        ]

    def _nomes_das_pecas_pendentes(self) -> list[str]:
        return [item.nome for item in self.pecas if item.quantidade_pendente > 0]

    def _validar_transicao(self, destino: StatusOS, *, de: Collection[StatusOS]) -> None:
        if self.status not in de:
            raise TransicaoDeStatusInvalida(self.status, destino)

    def _mudar_status(
        self,
        destino: StatusOS,
        *,
        de: Collection[StatusOS],
        origem: OrigemTransicao,
        usuario_id: UUID | None = None,
        motivo: str | None = None,
    ) -> datetime:
        """Único ponto que altera o status: valida a origem e registra a transição (RF-24).

        Devolve o instante do registro, que os timestamps da OS reaproveitam.
        """
        self._validar_transicao(destino, de=de)
        momento = datetime.now(UTC)
        self._acrescentar_ao_historico(
            HistoricoStatusOS(self.status, destino, momento, origem, usuario_id, motivo)
        )
        self.status = destino
        return momento

    def _acrescentar_ao_historico(self, registro: HistoricoStatusOS) -> None:
        object.__setattr__(self, "historico", (*self.historico, registro))

    def _validar_historico(self) -> None:
        """Um histórico reconstituído precisa estar completo e em ordem, e terminar no status."""
        historico = self.historico
        if not isinstance(historico, list | tuple) or not all(
            isinstance(registro, HistoricoStatusOS) for registro in historico
        ):
            raise OrdemServicoInvalida("o histórico da OS deve ser uma sequência de registros")
        for anterior, seguinte in zip(historico, historico[1:], strict=False):
            if seguinte.status_anterior != anterior.status_novo:
                raise OrdemServicoInvalida("os registros do histórico não estão encadeados")
        if historico and historico[-1].status_novo != self.status:
            raise OrdemServicoInvalida("o último registro do histórico não é o status da OS")
        object.__setattr__(self, "historico", tuple(historico))


def _registrada(data: datetime | None, descricao: str) -> datetime:
    if data is None:
        raise OrdemServicoInvalida(f"{descricao} da OS não foi registrada")
    return data


def _exigir_usuario(usuario_id: UUID) -> None:
    if not isinstance(usuario_id, UUID):
        raise OrdemServicoInvalida("o usuário é obrigatório")


def _somar(valores: Iterable[Valor]) -> Valor:
    total = Valor(0)
    for valor in valores:
        total = total.somar(valor)
    return total
