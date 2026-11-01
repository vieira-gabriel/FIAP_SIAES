"""Contrato do Swagger (`/docs`): esquema Bearer, respostas de erro e exemplos (RNF-16, RNF-03)."""

import pytest

from presentation.main import app

ROTAS_PUBLICAS = {
    ("get", "/health"),
    ("post", "/auth/login"),
    ("post", "/acompanhamento"),
    ("post", "/acompanhamento/aprovacao"),
    ("post", "/acompanhamento/rejeicao"),
}
ROTAS_COM_LIMITE = {
    ("post", "/acompanhamento"),
    ("post", "/acompanhamento/aprovacao"),
    ("post", "/acompanhamento/rejeicao"),
}
ERRO_RESPONSE = {"$ref": "#/components/schemas/ErroResponse"}


@pytest.fixture(scope="module")
def esquema() -> dict:
    return app.openapi()


def _operacoes(esquema: dict) -> list[tuple[str, str, dict]]:
    return [
        (metodo, caminho, operacao)
        for caminho, metodos in esquema["paths"].items()
        for metodo, operacao in metodos.items()
    ]


def test_declara_o_esquema_bearer_jwt_para_o_botao_authorize(esquema):
    assert esquema["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }


def test_so_as_rotas_publicas_ficam_sem_o_esquema_bearer(esquema):
    sem_bearer = {
        (metodo, caminho) for metodo, caminho, op in _operacoes(esquema) if not op.get("security")
    }

    assert sem_bearer == ROTAS_PUBLICAS


def test_rota_protegida_declara_401_e_403(esquema):
    for metodo, caminho, operacao in _operacoes(esquema):
        if (metodo, caminho) not in ROTAS_PUBLICAS:
            assert {"401", "403"} <= set(operacao["responses"]), (metodo, caminho)


def test_rota_publica_de_acompanhamento_declara_429(esquema):
    for metodo, caminho, operacao in _operacoes(esquema):
        assert ("429" in operacao["responses"]) == ((metodo, caminho) in ROTAS_COM_LIMITE)


def test_toda_rota_declara_o_erro_interno_com_o_corpo_de_erro(esquema):
    for metodo, caminho, operacao in _operacoes(esquema):
        corpo = operacao["responses"]["500"]["content"]["application/json"]["schema"]
        assert corpo == ERRO_RESPONSE, (metodo, caminho)


def test_toda_resposta_de_erro_usa_o_corpo_de_erro(esquema):
    for metodo, caminho, operacao in _operacoes(esquema):
        for codigo, resposta in operacao["responses"].items():
            if codigo.startswith(("4", "5")) and codigo != "503":
                corpo = resposta["content"]["application/json"]["schema"]
                assert corpo == ERRO_RESPONSE, (metodo, caminho, codigo)


def test_nao_documenta_o_corpo_de_validacao_do_fastapi(esquema):
    assert "HTTPValidationError" not in esquema["components"]["schemas"]
    assert "ValidationError" not in esquema["components"]["schemas"]


def test_toda_rota_tem_descricao(esquema):
    for metodo, caminho, operacao in _operacoes(esquema):
        assert operacao.get("description"), (metodo, caminho)


def test_o_corpo_de_erro_traz_codigo_mensagem_e_detalhes(esquema):
    assert set(esquema["components"]["schemas"]["ErroResponse"]["properties"]) == {
        "codigo",
        "mensagem",
        "detalhes",
    }


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("post", "/ordens-servico"),
        ("get", "/ordens-servico"),
        ("post", "/ordens-servico/{id}/mecanico"),
        ("post", "/ordens-servico/{id}/pecas"),
    ],
)
def test_rotas_da_os_que_respondem_400_declaram_o_400(esquema, metodo, caminho):
    assert "400" in esquema["paths"][caminho][metodo]["responses"]


def test_campos_de_identificador_e_filtros_tem_exemplo(esquema):
    schemas = esquema["components"]["schemas"]
    for nome, campo in [
        ("IncluirServicoRequest", "servico_id"),
        ("IncluirPecaRequest", "peca_id"),
        ("CadastrarVeiculoRequest", "cliente_id"),
        ("LoginRequest", "senha"),
    ]:
        assert schemas[nome]["properties"][campo]["examples"], (nome, campo)
    parametros = {p["name"]: p for p in esquema["paths"]["/ordens-servico"]["get"]["parameters"]}
    assert all(p.get("description") for p in parametros.values())
