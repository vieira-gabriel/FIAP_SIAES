from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.token_service import TokenService
from application.ports.verificador_do_banco import VerificadorDoBanco
from application.use_cases.atualizar_cliente import AtualizarCliente
from application.use_cases.atualizar_veiculo import AtualizarVeiculo
from application.use_cases.autenticar_usuario import AutenticarUsuario
from application.use_cases.cadastrar_cliente import CadastrarCliente
from application.use_cases.cadastrar_veiculo import CadastrarVeiculo
from application.use_cases.criar_carga_inicial import CriarCargaInicial, SenhasDaCargaInicial
from application.use_cases.detalhar_cliente import DetalharCliente
from application.use_cases.detalhar_veiculo import DetalharVeiculo
from application.use_cases.excluir_cliente import ExcluirCliente
from application.use_cases.excluir_veiculo import ExcluirVeiculo
from application.use_cases.listar_clientes import ListarClientes
from application.use_cases.listar_veiculos import ListarVeiculos
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.veiculo_repository import VeiculoRepository
from infrastructure.config import Configuracao, carregar_configuracao
from infrastructure.database.engine import criar_engine, criar_fabrica_de_sessoes
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.database.verificador_do_banco import VerificadorDoBancoSqlAlchemy
from infrastructure.repositories.postgres_cliente_repository import PostgresClienteRepository
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.repositories.postgres_veiculo_repository import PostgresVeiculoRepository
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
    montar_caso_de_uso: Callable[[AsyncSession], T],
) -> Callable[[Request], AsyncIterator[T]]:
    """Cada requisição recebe a própria unidade de trabalho; os repositórios dividem a sessão."""

    async def obter(request: Request) -> AsyncIterator[T]:
        async with UnidadeDeTrabalhoSqlAlchemy(request.app.state.fabrica_de_sessoes) as unidade:
            yield montar_caso_de_uso(unidade.sessao)

    return obter


def _com_repositorio_de_clientes[T](
    caso_de_uso: Callable[[ClienteRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(lambda sessao: caso_de_uso(PostgresClienteRepository(sessao)))


def _com_repositorio_de_veiculos[T](
    caso_de_uso: Callable[[VeiculoRepository], T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(lambda sessao: caso_de_uso(PostgresVeiculoRepository(sessao)))


def _com_repositorios_de_clientes_e_veiculos[T](
    caso_de_uso: Callable[..., T],
) -> Callable[[Request], AsyncIterator[T]]:
    return _por_requisicao(
        lambda sessao: caso_de_uso(
            clientes=PostgresClienteRepository(sessao),
            veiculos=PostgresVeiculoRepository(sessao),
        )
    )


obter_cadastrar_cliente = _com_repositorio_de_clientes(CadastrarCliente)
obter_atualizar_cliente = _com_repositorio_de_clientes(AtualizarCliente)
obter_listar_clientes = _com_repositorio_de_clientes(ListarClientes)
obter_detalhar_cliente = _com_repositorio_de_clientes(DetalharCliente)
obter_excluir_cliente = _com_repositorio_de_clientes(ExcluirCliente)

obter_cadastrar_veiculo = _com_repositorios_de_clientes_e_veiculos(CadastrarVeiculo)
obter_atualizar_veiculo = _com_repositorio_de_veiculos(AtualizarVeiculo)
obter_listar_veiculos = _com_repositorio_de_veiculos(ListarVeiculos)
obter_detalhar_veiculo = _com_repositorio_de_veiculos(DetalharVeiculo)
obter_excluir_veiculo = _com_repositorio_de_veiculos(ExcluirVeiculo)


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
