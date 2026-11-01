"""Proteções de entrada pela API real: XSS nos campos de texto livre e SQL Injection (RNF-04)."""

import pytest
from sqlalchemy import text

SCRIPT = "<script>alert(1)</script>"
EMAIL_COM_SCRIPT = "<script>alert(1)</script>@exemplo.com"
INJECAO_SQL = "Maria'); DROP TABLE clientes; --"

CLIENTE = {
    "nome": "Maria Silva",
    "documento": "529.982.247-25",
    "email": "maria@exemplo.com",
    "telefone": "11987654321",
}
SERVICO = {
    "codigo": "SRV-001",
    "nome": "Troca de óleo",
    "descricao": "Troca do óleo e do filtro",
    "valor_base": "120.00",
    "tempo_estimado_minutos": 45,
}
PECA = {
    "codigo_referencia": "FLT-001",
    "nome": "Filtro de óleo",
    "preco_unitario": "35.90",
    "prazo_reposicao_dias": 3,
}
USUARIO = {
    "nome": "Ana Atendente",
    "email": "ana@oficina.com",
    "senha": "senha-forte-123",
    "perfil": "ATENDENTE",
}


@pytest.mark.parametrize(
    ("rota", "corpo", "campo"),
    [
        ("/clientes", CLIENTE, "nome"),
        ("/clientes", CLIENTE, "telefone"),
        ("/servicos", SERVICO, "nome"),
        ("/servicos", SERVICO, "descricao"),
        ("/servicos", SERVICO, "codigo"),
        ("/pecas", PECA, "nome"),
        ("/pecas", PECA, "codigo_referencia"),
        ("/usuarios", USUARIO, "nome"),
    ],
)
async def test_texto_livre_com_marcacao_html_e_recusado_com_400(
    cliente_http, gerente, rota, corpo, campo
):
    resposta = await cliente_http.post(rota, json=corpo | {campo: SCRIPT}, headers=gerente)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"
    assert SCRIPT not in resposta.text


@pytest.mark.parametrize(("rota", "corpo"), [("/clientes", CLIENTE), ("/usuarios", USUARIO)])
async def test_email_com_marcacao_html_e_recusado_com_400(cliente_http, gerente, rota, corpo):
    resposta = await cliente_http.post(
        rota, json=corpo | {"email": EMAIL_COM_SCRIPT}, headers=gerente
    )

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"
    assert EMAIL_COM_SCRIPT not in resposta.text


@pytest.mark.parametrize("campo", ["marca", "modelo"])
async def test_texto_do_veiculo_com_marcacao_html_e_recusado(cliente_http, gerente, campo):
    cliente = (await cliente_http.post("/clientes", json=CLIENTE, headers=gerente)).json()
    veiculo = {
        "cliente_id": cliente["id"],
        "placa": "ABC1D23",
        "marca": "Fiat",
        "modelo": "Uno",
        "ano": 2015,
    }

    resposta = await cliente_http.post("/veiculos", json=veiculo | {campo: SCRIPT}, headers=gerente)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_atualizacao_com_marcacao_html_e_recusada_e_mantem_o_nome(cliente_http, gerente):
    cliente = (await cliente_http.post("/clientes", json=CLIENTE, headers=gerente)).json()

    resposta = await cliente_http.put(
        f"/clientes/{cliente['id']}", json=CLIENTE | {"nome": SCRIPT}, headers=gerente
    )

    assert resposta.status_code == 400
    detalhe = await cliente_http.get(f"/clientes/{cliente['id']}", headers=gerente)
    assert detalhe.json()["nome"] == "Maria Silva"


async def test_texto_com_sql_e_guardado_e_devolvido_como_texto_e_a_tabela_continua(
    cliente_http, gerente, conexao
):
    criado = await cliente_http.post(
        "/clientes", json=CLIENTE | {"nome": INJECAO_SQL}, headers=gerente
    )

    assert criado.status_code == 201
    assert criado.json()["nome"] == INJECAO_SQL
    assert await conexao.scalar(text("SELECT count(*) FROM clientes")) == 1
    assert await conexao.scalar(text("SELECT nome FROM clientes")) == INJECAO_SQL


@pytest.mark.parametrize(
    "filtro",
    [
        {"documento": "' OR '1'='1"},
        {"documento": "529.982.247-25'; DROP TABLE ordens_servico; --"},
        {"placa": "' OR '1'='1"},
        {"placa": "ABC1D23'; DROP TABLE veiculos; --"},
    ],
)
async def test_filtro_da_listagem_com_sql_e_recusado_como_valor_invalido(
    cliente_http, gerente, conexao, filtro
):
    resposta = await cliente_http.get("/ordens-servico", params=filtro, headers=gerente)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"
    assert await conexao.scalar(text("SELECT to_regclass('ordens_servico')")) is not None
    assert await conexao.scalar(text("SELECT to_regclass('veiculos')")) is not None
