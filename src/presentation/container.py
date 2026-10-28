from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import State

from application.ports.password_hasher import PasswordHasher
from application.ports.token_service import TokenService
from application.ports.verificador_do_banco import VerificadorDoBanco
from application.use_cases.alterar_senha_do_usuario import AlterarSenhaDoUsuario
from application.use_cases.atualizar_cliente import AtualizarCliente
from application.use_cases.atualizar_servico import AtualizarServico
from application.use_cases.atualizar_usuario import AtualizarUsuario
from application.use_cases.autenticar_usuario import AutenticarUsuario
from application.use_cases.cadastrar_cliente import CadastrarCliente
from application.use_cases.cadastrar_servico import CadastrarServico
from application.use_cases.cadastrar_usuario import CadastrarUsuario
from application.use_cases.criar_carga_inicial import CriarCargaInicial, SenhasDaCargaInicial
from application.use_cases.desativar_usuario import DesativarUsuario
from application.use_cases.detalhar_cliente import DetalharCliente
from application.use_cases.detalhar_servico import DetalharServico
from application.use_cases.detalhar_usuario import DetalharUsuario
from application.use_cases.excluir_cliente import ExcluirCliente
from application.use_cases.excluir_servico import ExcluirServico
from application.use_cases.listar_clientes import ListarClientes
from application.use_cases.listar_servicos import ListarServicos
from application.use_cases.listar_usuarios import ListarUsuarios
from application.use_cases.reativar_usuario import ReativarUsuario
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.servico_repository import ServicoRepository
from domain.repositories.usuario_repository import UsuarioRepository
from infrastructure.config import Configuracao, carregar_configuracao
from infrastructure.database.engine import criar_engine, criar_fabrica_de_sessoes
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.database.verificador_do_banco import VerificadorDoBancoSqlAlchemy
from infrastructure.repositories.postgres_cliente_repository import PostgresClienteRepository
from infrastructure.repositories.postgres_servico_repository import PostgresServicoRepository
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from infrastructure.security.jwt_token_service import JwtTokenService


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


obter_cadastrar_cliente = _com_repositorio_de_clientes(CadastrarCliente)
obter_atualizar_cliente = _com_repositorio_de_clientes(AtualizarCliente)
obter_listar_clientes = _com_repositorio_de_clientes(ListarClientes)
obter_detalhar_cliente = _com_repositorio_de_clientes(DetalharCliente)
obter_excluir_cliente = _com_repositorio_de_clientes(ExcluirCliente)

obter_cadastrar_servico = _com_repositorio_de_servicos(CadastrarServico)
obter_atualizar_servico = _com_repositorio_de_servicos(AtualizarServico)
obter_listar_servicos = _com_repositorio_de_servicos(ListarServicos)
obter_detalhar_servico = _com_repositorio_de_servicos(DetalharServico)
obter_excluir_servico = _com_repositorio_de_servicos(ExcluirServico)

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
