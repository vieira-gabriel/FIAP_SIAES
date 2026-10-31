from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import State

from application.events.event_dispatcher import EventDispatcher, EventHandler
from application.handlers.alocacao_pecas_pendentes_handler import AlocacaoPecasPendentesHandler
from application.handlers.baixa_estoque_handler import BaixaEstoqueHandler
from application.handlers.estorno_reservas_handler import EstornoReservasHandler
from application.handlers.reserva_pecas_handler import ReservaPecasHandler
from application.ports.password_hasher import PasswordHasher
from application.ports.token_service import TokenService
from application.ports.verificador_do_banco import VerificadorDoBanco
from application.use_cases.ajustar_quantidade_fisica_da_peca import AjustarQuantidadeFisicaDaPeca
from application.use_cases.alterar_senha_do_usuario import AlterarSenhaDoUsuario
from application.use_cases.aprovar_orcamento import AprovarOrcamento
from application.use_cases.atribuir_mecanico import AtribuirMecanico
from application.use_cases.atualizar_cliente import AtualizarCliente
from application.use_cases.atualizar_peca import AtualizarPeca
from application.use_cases.atualizar_servico import AtualizarServico
from application.use_cases.atualizar_usuario import AtualizarUsuario
from application.use_cases.atualizar_veiculo import AtualizarVeiculo
from application.use_cases.autenticar_usuario import AutenticarUsuario
from application.use_cases.cadastrar_cliente import CadastrarCliente
from application.use_cases.cadastrar_peca import CadastrarPeca
from application.use_cases.cadastrar_servico import CadastrarServico
from application.use_cases.cadastrar_usuario import CadastrarUsuario
from application.use_cases.cadastrar_veiculo import CadastrarVeiculo
from application.use_cases.cancelar_os import CancelarOS
from application.use_cases.consultar_os_publica import ConsultarOSPublica
from application.use_cases.criar_carga_inicial import CriarCargaInicial, SenhasDaCargaInicial
from application.use_cases.criar_os import CriarOS
from application.use_cases.desativar_usuario import DesativarUsuario
from application.use_cases.detalhar_cliente import DetalharCliente
from application.use_cases.detalhar_ordem_servico import DetalharOrdemServico
from application.use_cases.detalhar_peca import DetalharPeca
from application.use_cases.detalhar_servico import DetalharServico
from application.use_cases.detalhar_usuario import DetalharUsuario
from application.use_cases.detalhar_veiculo import DetalharVeiculo
from application.use_cases.excluir_cliente import ExcluirCliente
from application.use_cases.excluir_peca import ExcluirPeca
from application.use_cases.excluir_servico import ExcluirServico
from application.use_cases.excluir_veiculo import ExcluirVeiculo
from application.use_cases.finalizar_orcamento import FinalizarOrcamento
from application.use_cases.incluir_peca_na_os import IncluirPecaNaOS
from application.use_cases.incluir_servico_na_os import IncluirServicoNaOS
from application.use_cases.iniciar_execucao import IniciarExecucao
from application.use_cases.listar_clientes import ListarClientes
from application.use_cases.listar_ordens_servico import ListarOrdensServico
from application.use_cases.listar_pecas import ListarPecas
from application.use_cases.listar_servicos import ListarServicos
from application.use_cases.listar_usuarios import ListarUsuarios
from application.use_cases.listar_veiculos import ListarVeiculos
from application.use_cases.localizar_os_do_titular import LocalizarOSDoTitular
from application.use_cases.reativar_usuario import ReativarUsuario
from application.use_cases.remover_peca_da_os import RemoverPecaDaOS
from application.use_cases.remover_servico_da_os import RemoverServicoDaOS
from application.use_cases.repor_peca import ReporPeca
from domain.events.domain_event import DomainEvent
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.events.os_cancelada_event import OSCanceladaEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.estoque_repository import EstoqueRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository
from domain.repositories.peca_repository import PecaRepository
from domain.repositories.servico_repository import ServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository
from domain.repositories.veiculo_repository import VeiculoRepository
from infrastructure.config import Configuracao, carregar_configuracao
from infrastructure.database.engine import criar_engine, criar_fabrica_de_sessoes
from infrastructure.database.repeticao_em_impasse import com_repeticao_em_impasse
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.database.verificador_do_banco import VerificadorDoBancoSqlAlchemy
from infrastructure.repositories.postgres_cliente_repository import PostgresClienteRepository
from infrastructure.repositories.postgres_estoque_repository import PostgresEstoqueRepository
from infrastructure.repositories.postgres_ordem_servico_repository import (
    PostgresOrdemServicoRepository,
)
from infrastructure.repositories.postgres_peca_repository import PostgresPecaRepository
from infrastructure.repositories.postgres_servico_repository import PostgresServicoRepository
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.repositories.postgres_veiculo_repository import PostgresVeiculoRepository
from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from infrastructure.security.jwt_token_service import JwtTokenService
from presentation.middlewares.rate_limit import configurar_limite_publico


def montar_dependencias(app: FastAPI) -> None:
    """Falha na subida, antes de aceitar requisições, se faltar variável obrigatória (RNF-06)."""
    configuracao = carregar_configuracao()
    engine = criar_engine(
        host=configuracao.postgres_host,
        porta=configuracao.postgres_port,
        banco=configuracao.postgres_db,
        usuario=configuracao.postgres_user,
        senha=configuracao.postgres_password.get_secret_value(),
    )
    app.state.engine = engine
    app.state.fabrica_de_sessoes = criar_fabrica_de_sessoes(engine)
    app.state.token_service = JwtTokenService(
        configuracao.jwt_secret_key.get_secret_value(),
        expiracao_horas=configuracao.jwt_expiration_hours,
    )
    app.state.password_hasher = BcryptPasswordHasher()
    app.state.verificador_do_banco = VerificadorDoBancoSqlAlchemy(engine)
    app.state.senhas_da_carga_inicial = _senhas_da_carga_inicial(configuracao)
    app.state.fabricas_de_handlers = _fabricas_de_handlers()
    configurar_limite_publico(configuracao.rate_limit_publico)


async def executar_carga_inicial(app: FastAPI) -> None:
    """Roda depois das migrations, que o container aplica antes do Uvicorn (RF-03)."""
    async with UnidadeDeTrabalhoSqlAlchemy(app.state.fabrica_de_sessoes) as unidade:
        carga_inicial = CriarCargaInicial(
            PostgresUsuarioRepository(unidade.sessao), app.state.password_hasher
        )
        await carga_inicial.executar(app.state.senhas_da_carga_inicial)


async def encerrar_dependencias(app: FastAPI) -> None:
    await app.state.engine.dispose()


def obter_token_service(request: Request) -> TokenService:
    return request.app.state.token_service


def obter_verificador_do_banco(request: Request) -> VerificadorDoBanco:
    return request.app.state.verificador_do_banco


async def obter_autenticar_usuario(request: Request) -> AsyncIterator[AutenticarUsuario]:
    estado = request.app.state
    async with UnidadeDeTrabalhoSqlAlchemy(estado.fabrica_de_sessoes) as unidade:
        yield AutenticarUsuario(
            PostgresUsuarioRepository(unidade.sessao),
            estado.password_hasher,
            estado.token_service,
        )


def _por_requisicao[T](
    montar: Callable[[AsyncSession, State], T],
) -> Callable[[Request], AsyncIterator[T]]:
    """Cada requisição recebe a própria unidade de trabalho e os próprios repositórios."""

    async def obter(request: Request) -> AsyncIterator[T]:
        async with UnidadeDeTrabalhoSqlAlchemy(request.app.state.fabrica_de_sessoes) as unidade:
            yield montar(unidade.sessao, request.app.state)

    return obter


def _com_repositorio_de_clientes[T](
    caso_de_uso: Callable[[ClienteRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(lambda sessao, _: caso_de_uso(PostgresClienteRepository(sessao)))


def _com_repositorio_de_servicos[T](
    caso_de_uso: Callable[[ServicoRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(lambda sessao, _: caso_de_uso(PostgresServicoRepository(sessao)))


def _com_repositorio_de_veiculos[T](
    caso_de_uso: Callable[[VeiculoRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(lambda sessao, _: caso_de_uso(PostgresVeiculoRepository(sessao)))


def _com_repositorios_de_clientes_e_veiculos[T](
    caso_de_uso: Callable[..., T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(
        lambda sessao, _: caso_de_uso(
            clientes=PostgresClienteRepository(sessao),
            veiculos=PostgresVeiculoRepository(sessao),
        )
    )


def _com_repositorio_de_usuarios[T](
    caso_de_uso: Callable[[UsuarioRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(lambda sessao, _: caso_de_uso(PostgresUsuarioRepository(sessao)))


def _com_repositorio_de_usuarios_e_hash[T](
    caso_de_uso: Callable[[UsuarioRepository, PasswordHasher], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(
        lambda sessao, estado: caso_de_uso(
            PostgresUsuarioRepository(sessao), estado.password_hasher
        )
    )


def _com_repositorios_de_pecas[T](
    caso_de_uso: Callable[[PecaRepository, EstoqueRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(
        lambda sessao, _: caso_de_uso(
            PostgresPecaRepository(sessao), PostgresEstoqueRepository(sessao)
        )
    )


def _com_repositorios_de_pecas_e_eventos[T](
    caso_de_uso: Callable[[PecaRepository, EstoqueRepository, EventDispatcher], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(
        lambda sessao, estado: com_repeticao_em_impasse(
            caso_de_uso(
                PostgresPecaRepository(sessao),
                PostgresEstoqueRepository(sessao),
                _eventos_da_requisicao(sessao, estado),
            ),
            sessao,
        )
    )


def _fabricas_de_handlers() -> list[
    tuple[type[DomainEvent], Callable[[AsyncSession], EventHandler]]
]:
    """Os handlers da aplicação: cada um nasce por requisição, sobre a sessão dela."""
    return [
        (
            OrcamentoFinalizadoEvent,
            lambda sessao: ReservaPecasHandler(
                PostgresOrdemServicoRepository(sessao), PostgresEstoqueRepository(sessao)
            ),
        ),
        (
            SaldoPecaAtualizadoEvent,
            lambda sessao: AlocacaoPecasPendentesHandler(
                PostgresOrdemServicoRepository(sessao), PostgresEstoqueRepository(sessao)
            ),
        ),
        (
            OSCanceladaEvent,
            lambda sessao: EstornoReservasHandler(PostgresEstoqueRepository(sessao)),
        ),
        (
            ExecucaoIniciadaEvent,
            lambda sessao: BaixaEstoqueHandler(PostgresEstoqueRepository(sessao)),
        ),
    ]


def _eventos_da_requisicao(sessao: AsyncSession, estado: State) -> EventDispatcher:
    """Um despacho por requisição, com os handlers presos à sessão da unidade de trabalho: a
    reação ao evento grava na mesma transação da operação, e uma falha desfaz as duas (RNF-08).

    Os handlers vêm de `app.state.fabricas_de_handlers`, uma lista de pares
    `(tipo_do_evento, fabrica)`; a fabrica recebe a sessão e devolve o handler. A alocação às OS
    com peça pendente (RF-19, #94) entra por essa lista.
    """
    despachador = EventDispatcher()
    for tipo_do_evento, fabrica in estado.fabricas_de_handlers:
        despachador.registrar(tipo_do_evento, fabrica(sessao))
    return despachador


def _com_repositorios_de_pecas_e_ordens[T](
    caso_de_uso: Callable[[PecaRepository, EstoqueRepository, OrdemServicoRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(
        lambda sessao, _: caso_de_uso(
            PostgresPecaRepository(sessao),
            PostgresEstoqueRepository(sessao),
            PostgresOrdemServicoRepository(sessao),
        )
    )


obter_cadastrar_cliente = _com_repositorio_de_clientes(CadastrarCliente)
obter_atualizar_cliente = _com_repositorio_de_clientes(AtualizarCliente)
obter_listar_clientes = _com_repositorio_de_clientes(ListarClientes)
obter_detalhar_cliente = _com_repositorio_de_clientes(DetalharCliente)
obter_excluir_cliente = _com_repositorios_de_clientes_e_veiculos(ExcluirCliente)

obter_cadastrar_veiculo = _com_repositorios_de_clientes_e_veiculos(CadastrarVeiculo)
obter_atualizar_veiculo = _com_repositorio_de_veiculos(AtualizarVeiculo)
obter_listar_veiculos = _com_repositorio_de_veiculos(ListarVeiculos)
obter_detalhar_veiculo = _com_repositorio_de_veiculos(DetalharVeiculo)
obter_excluir_veiculo = _com_repositorio_de_veiculos(ExcluirVeiculo)


def _com_abertura_de_os[T](
    caso_de_uso: Callable[..., T],
) -> Callable[[Request], AsyncIterator[T]]:
    """Cliente, veículo e OS na mesma sessão: a abertura grava tudo ou nada (RNF-08)."""
    return _por_requisicao(
        lambda sessao, _: caso_de_uso(
            PostgresClienteRepository(sessao),
            PostgresVeiculoRepository(sessao),
            PostgresOrdemServicoRepository(sessao),
        )
    )


obter_criar_os = _com_abertura_de_os(CriarOS)
obter_atribuir_mecanico = _por_requisicao(
    lambda sessao, _: AtribuirMecanico(
        PostgresOrdemServicoRepository(sessao), PostgresUsuarioRepository(sessao)
    )
)
obter_incluir_servico_na_os = _por_requisicao(
    lambda sessao, _: IncluirServicoNaOS(
        PostgresOrdemServicoRepository(sessao), PostgresServicoRepository(sessao)
    )
)
obter_incluir_peca_na_os = _por_requisicao(
    lambda sessao, _: IncluirPecaNaOS(
        PostgresOrdemServicoRepository(sessao), PostgresPecaRepository(sessao)
    )
)
obter_remover_servico_da_os = _por_requisicao(
    lambda sessao, _: RemoverServicoDaOS(PostgresOrdemServicoRepository(sessao))
)
obter_remover_peca_da_os = _por_requisicao(
    lambda sessao, _: RemoverPecaDaOS(PostgresOrdemServicoRepository(sessao))
)
obter_finalizar_orcamento = _por_requisicao(
    lambda sessao, estado: com_repeticao_em_impasse(
        FinalizarOrcamento(
            PostgresOrdemServicoRepository(sessao),
            PostgresEstoqueRepository(sessao),
            PostgresServicoRepository(sessao),
            PostgresPecaRepository(sessao),
            _eventos_da_requisicao(sessao, estado),
        ),
        sessao,
    )
)
obter_cancelar_os = _por_requisicao(
    lambda sessao, estado: com_repeticao_em_impasse(
        CancelarOS(PostgresOrdemServicoRepository(sessao), _eventos_da_requisicao(sessao, estado)),
        sessao,
    )
)
obter_iniciar_execucao = _por_requisicao(
    lambda sessao, estado: com_repeticao_em_impasse(
        IniciarExecucao(
            PostgresOrdemServicoRepository(sessao),
            PostgresUsuarioRepository(sessao),
            _eventos_da_requisicao(sessao, estado),
        ),
        sessao,
    )
)
obter_detalhar_ordem_servico = _por_requisicao(
    lambda sessao, _: DetalharOrdemServico(
        PostgresOrdemServicoRepository(sessao),
        PostgresClienteRepository(sessao),
        PostgresVeiculoRepository(sessao),
    )
)


def _localizar_os_do_titular(sessao: AsyncSession) -> LocalizarOSDoTitular:
    return LocalizarOSDoTitular(
        PostgresOrdemServicoRepository(sessao), PostgresClienteRepository(sessao)
    )


obter_consultar_os_publica = _por_requisicao(
    lambda sessao, _: ConsultarOSPublica(_localizar_os_do_titular(sessao))
)
obter_aprovar_orcamento = _por_requisicao(
    lambda sessao, _: AprovarOrcamento(
        _localizar_os_do_titular(sessao), PostgresOrdemServicoRepository(sessao)
    )
)
obter_listar_ordens_servico = _por_requisicao(
    lambda sessao, _: ListarOrdensServico(
        PostgresOrdemServicoRepository(sessao),
        PostgresClienteRepository(sessao),
        PostgresVeiculoRepository(sessao),
        PostgresUsuarioRepository(sessao),
    )
)
obter_cadastrar_servico = _com_repositorio_de_servicos(CadastrarServico)
obter_atualizar_servico = _com_repositorio_de_servicos(AtualizarServico)
obter_listar_servicos = _com_repositorio_de_servicos(ListarServicos)
obter_detalhar_servico = _com_repositorio_de_servicos(DetalharServico)
obter_excluir_servico = _com_repositorio_de_servicos(ExcluirServico)

obter_cadastrar_peca = _com_repositorios_de_pecas(CadastrarPeca)
obter_atualizar_peca = _com_repositorios_de_pecas(AtualizarPeca)
obter_listar_pecas = _com_repositorios_de_pecas(ListarPecas)
obter_detalhar_peca = _com_repositorios_de_pecas(DetalharPeca)
obter_excluir_peca = _com_repositorios_de_pecas_e_ordens(ExcluirPeca)
obter_repor_peca = _com_repositorios_de_pecas_e_eventos(ReporPeca)
obter_ajustar_quantidade_fisica_da_peca = _com_repositorios_de_pecas_e_eventos(
    AjustarQuantidadeFisicaDaPeca
)

obter_cadastrar_usuario = _com_repositorio_de_usuarios_e_hash(CadastrarUsuario)
obter_alterar_senha_do_usuario = _com_repositorio_de_usuarios_e_hash(AlterarSenhaDoUsuario)
obter_listar_usuarios = _com_repositorio_de_usuarios(ListarUsuarios)
obter_detalhar_usuario = _com_repositorio_de_usuarios(DetalharUsuario)
obter_atualizar_usuario = _com_repositorio_de_usuarios(AtualizarUsuario)
obter_desativar_usuario = _com_repositorio_de_usuarios(DesativarUsuario)
obter_reativar_usuario = _com_repositorio_de_usuarios(ReativarUsuario)


def _senhas_da_carga_inicial(configuracao: Configuracao) -> SenhasDaCargaInicial:
    senha_gerente = configuracao.admin_password.get_secret_value()
    if not configuracao.seed_demo:
        return SenhasDaCargaInicial(gerente=senha_gerente)
    # Com SEED_DEMO=true, a configuração já recusou a subida sem as duas senhas de demonstração.
    return SenhasDaCargaInicial(
        gerente=senha_gerente,
        atendente=configuracao.demo_atendente_password.get_secret_value(),
        mecanico=configuracao.demo_mecanico_password.get_secret_value(),
    )
