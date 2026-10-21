from typing import Annotated, Self

from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TextoObrigatorio = Annotated[str, Field(min_length=1)]
SegredoObrigatorio = Annotated[SecretStr, Field(min_length=1)]


class ConfiguracaoInvalida(Exception):
    """Variável de ambiente obrigatória ausente ou com valor inválido (RNF-06)."""

    def __init__(self, variaveis: list[str]):
        super().__init__(
            "Variáveis de ambiente ausentes ou inválidas: " + ", ".join(variaveis) + "."
        )
        self.variaveis = variaveis


class Configuracao(BaseSettings):
    """Variáveis listadas no `.env.example`.

    Senhas e chaves não têm valor padrão: sem elas a aplicação não inicia (RNF-06, RF-03).
    O `.env.example` traz essas variáveis vazias, por isso o valor vazio também é recusado.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: TextoObrigatorio
    postgres_port: int = Field(gt=0)
    postgres_db: TextoObrigatorio
    postgres_user: TextoObrigatorio
    postgres_password: SegredoObrigatorio

    jwt_secret_key: SegredoObrigatorio
    jwt_expiration_hours: int = Field(default=24, gt=0)

    admin_password: SegredoObrigatorio
    seed_demo: bool = False
    demo_atendente_password: SecretStr | None = None
    demo_mecanico_password: SecretStr | None = None

    rate_limit_publico: TextoObrigatorio = "10/minute"

    @model_validator(mode="after")
    def _exigir_senhas_de_demonstracao(self) -> Self:
        if not self.seed_demo:
            return self
        ausentes = [
            nome.upper()
            for nome in ("demo_atendente_password", "demo_mecanico_password")
            if not _preenchido(getattr(self, nome))
        ]
        if ausentes:
            raise ConfiguracaoInvalida(ausentes)
        return self


def carregar_configuracao(**valores) -> Configuracao:
    """Lê o ambiente na subida da aplicação, nunca no import do módulo (guia, seção 8.1).

    Os `valores` repassam opções ao pydantic-settings, como `_env_file=None` nos testes.
    A causa original é descartada porque a mensagem do pydantic repete o valor recebido.
    """
    try:
        return Configuracao(**valores)
    except ValidationError as erro:
        variaveis = sorted({str(detalhe["loc"][0]).upper() for detalhe in erro.errors()})
        raise ConfiguracaoInvalida(variaveis) from None


def _preenchido(senha: SecretStr | None) -> bool:
    return senha is not None and senha.get_secret_value() != ""
