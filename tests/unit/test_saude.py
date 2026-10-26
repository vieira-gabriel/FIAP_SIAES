import httpx
import pytest

from application.ports.verificador_do_banco import VerificadorDoBanco
from presentation.container import obter_verificador_do_banco
from presentation.main import app


class VerificadorDoBancoFalso(VerificadorDoBanco):
    def __init__(self, disponivel: bool):
        self._disponivel = disponivel

    async def esta_disponivel(self):
        return self._disponivel


@pytest.fixture
async def cliente():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://teste"
    ) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _banco_disponivel(disponivel: bool) -> None:
    app.dependency_overrides[obter_verificador_do_banco] = lambda: VerificadorDoBancoFalso(
        disponivel
    )


async def test_health_com_banco_disponivel_retorna_200(cliente):
    _banco_disponivel(True)

    resposta = await cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "status": "online",
        "banco": "disponivel",
        "message": "Serviço operando normalmente.",
    }


async def test_health_com_banco_indisponivel_retorna_503(cliente):
    _banco_disponivel(False)

    resposta = await cliente.get("/health")

    assert resposta.status_code == 503
    assert resposta.json() == {
        "status": "indisponivel",
        "banco": "indisponivel",
        "message": "Banco de dados indisponível.",
    }


async def test_openapi_identifica_a_api(cliente):
    esquema = (await cliente.get("/openapi.json")).json()

    assert esquema["info"]["title"] == "SIAES - API da Oficina Mecânica"
    assert esquema["info"]["version"] == "0.1.0"
    assert esquema["info"]["description"]


async def test_openapi_declara_o_esquema_bearer_jwt_para_o_botao_authorize(cliente):
    esquema = (await cliente.get("/openapi.json")).json()

    assert esquema["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }


async def test_openapi_documenta_o_503_do_health(cliente):
    esquema = (await cliente.get("/openapi.json")).json()

    respostas = esquema["paths"]["/health"]["get"]["responses"]
    assert {"200", "503"} <= set(respostas)
