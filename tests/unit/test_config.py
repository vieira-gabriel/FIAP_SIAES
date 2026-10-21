import pytest
from fastapi.testclient import TestClient

from infrastructure.config import ConfiguracaoInvalida, carregar_configuracao
from presentation.main import app

VARIAVEIS_VALIDAS = {
    "POSTGRES_HOST": "db",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "siaes",
    "POSTGRES_USER": "siaes",
    "POSTGRES_PASSWORD": "senha-do-banco",
    "JWT_SECRET_KEY": "chave-de-teste-com-pelo-menos-32-bytes!!",
    "ADMIN_PASSWORD": "senha-do-admin",
}

OPCIONAIS = [
    "JWT_EXPIRATION_HOURS",
    "SEED_DEMO",
    "DEMO_ATENDENTE_PASSWORD",
    "DEMO_MECANICO_PASSWORD",
    "RATE_LIMIT_PUBLICO",
]


@pytest.fixture
def ambiente(monkeypatch, tmp_path):
    """Ambiente válido e isolado: o `.env` é lido do diretório atual, que fica vazio."""
    monkeypatch.chdir(tmp_path)
    for nome in OPCIONAIS:
        monkeypatch.delenv(nome, raising=False)
    for nome, valor in VARIAVEIS_VALIDAS.items():
        monkeypatch.setenv(nome, valor)
    return monkeypatch


def _erro_ao_carregar() -> ConfiguracaoInvalida:
    with pytest.raises(ConfiguracaoInvalida) as erro:
        carregar_configuracao()
    return erro.value


def test_configuracao_valida_usa_os_padroes_do_env_example(ambiente):
    configuracao = carregar_configuracao()

    assert configuracao.postgres_port == 5432
    assert configuracao.jwt_secret_key.get_secret_value() == VARIAVEIS_VALIDAS["JWT_SECRET_KEY"]
    assert configuracao.jwt_expiration_hours == 24
    assert configuracao.seed_demo is False
    assert configuracao.rate_limit_publico == "10/minute"


@pytest.mark.parametrize("nome", sorted(VARIAVEIS_VALIDAS))
def test_variavel_obrigatoria_ausente_impede_o_carregamento(ambiente, nome):
    ambiente.delenv(nome)

    erro = _erro_ao_carregar()

    assert erro.variaveis == [nome]
    assert nome in str(erro)


@pytest.mark.parametrize("nome", ["POSTGRES_PASSWORD", "JWT_SECRET_KEY", "ADMIN_PASSWORD"])
def test_segredo_vazio_como_no_env_example_impede_o_carregamento(ambiente, nome):
    ambiente.setenv(nome, "")

    assert _erro_ao_carregar().variaveis == [nome]


def test_lista_todas_as_variaveis_ausentes(ambiente):
    ambiente.delenv("JWT_SECRET_KEY")
    ambiente.delenv("ADMIN_PASSWORD")

    assert _erro_ao_carregar().variaveis == ["ADMIN_PASSWORD", "JWT_SECRET_KEY"]


def test_valor_invalido_nomeia_a_variavel_sem_expor_o_valor(ambiente):
    ambiente.setenv("JWT_EXPIRATION_HOURS", "0")

    erro = _erro_ao_carregar()

    assert erro.variaveis == ["JWT_EXPIRATION_HOURS"]
    assert erro.__cause__ is None


def test_seed_demo_sem_senhas_de_demonstracao_impede_o_carregamento(ambiente):
    ambiente.setenv("SEED_DEMO", "true")
    ambiente.setenv("DEMO_ATENDENTE_PASSWORD", "")

    assert _erro_ao_carregar().variaveis == ["DEMO_ATENDENTE_PASSWORD", "DEMO_MECANICO_PASSWORD"]


def test_seed_demo_com_senhas_de_demonstracao(ambiente):
    ambiente.setenv("SEED_DEMO", "true")
    ambiente.setenv("DEMO_ATENDENTE_PASSWORD", "senha-atendente")
    ambiente.setenv("DEMO_MECANICO_PASSWORD", "senha-mecanico")

    configuracao = carregar_configuracao()

    assert configuracao.demo_mecanico_password.get_secret_value() == "senha-mecanico"


def test_senhas_de_demonstracao_sao_opcionais_sem_seed_demo(ambiente):
    ambiente.setenv("DEMO_ATENDENTE_PASSWORD", "")

    assert carregar_configuracao().seed_demo is False


def test_segredos_nao_aparecem_na_representacao(ambiente):
    texto = repr(carregar_configuracao())

    assert VARIAVEIS_VALIDAS["JWT_SECRET_KEY"] not in texto
    assert VARIAVEIS_VALIDAS["ADMIN_PASSWORD"] not in texto


def test_aplicacao_nao_inicia_sem_variavel_obrigatoria(ambiente):
    ambiente.delenv("JWT_SECRET_KEY")

    with pytest.raises(ConfiguracaoInvalida, match="JWT_SECRET_KEY"):
        with TestClient(app):
            pass


def test_aplicacao_inicia_com_configuracao_valida(ambiente):
    with TestClient(app) as cliente:
        assert cliente.get("/health").status_code == 200
        assert cliente.app.state.token_service is not None
