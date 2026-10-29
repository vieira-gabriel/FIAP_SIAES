"""Catálogo de serviços pelas rotas HTTP, com PostgreSQL real (RF-10, RF-11, RNF-13)."""

import pytest
from sqlalchemy import text

TROCA_DE_OLEO = {
    "codigo": "SRV-001",
    "nome": "Troca de óleo",
    "descricao": "Troca do óleo do motor e do filtro",
    "valor_base": "120.50",
    "tempo_estimado_minutos": 45,
}
ALINHAMENTO = {
    "codigo": "SRV-002",
    "nome": "Alinhamento",
    "descricao": "Alinhamento da direção",
    "valor_base": "80.00",
    "tempo_estimado_minutos": 30,
}


async def _cadastrar(cliente_http, cabecalho, dados=TROCA_DE_OLEO):
    return await cliente_http.post("/servicos", json=dados, headers=cabecalho)


async def test_gerente_cadastra_servico_com_valor_exato(cliente_http, gerente, conexao):
    resposta = await _cadastrar(cliente_http, gerente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert (corpo["codigo"], corpo["valor_base"], corpo["tempo_estimado_minutos"]) == (
        "SRV-001",
        "120.50",
        45,
    )
    valor_gravado = await conexao.scalar(
        text("SELECT valor_base FROM servicos WHERE codigo = 'SRV-001'")
    )
    assert str(valor_gravado) == "120.50"


@pytest.mark.parametrize("perfil", ["atendente", "mecanico", "gerente"])
async def test_todos_os_perfis_consultam_o_catalogo(cliente_http, gerente, perfil, request):
    criado = (await _cadastrar(cliente_http, gerente)).json()
    cabecalho = request.getfixturevalue(perfil)

    lista = await cliente_http.get("/servicos", headers=cabecalho)
    detalhe = await cliente_http.get(f"/servicos/{criado['id']}", headers=cabecalho)

    assert [s["id"] for s in lista.json()] == [criado["id"]]
    assert detalhe.json() == criado


async def test_listagem_em_ordem_de_nome(cliente_http, gerente):
    await _cadastrar(cliente_http, gerente, TROCA_DE_OLEO)
    await _cadastrar(cliente_http, gerente, ALINHAMENTO)

    resposta = await cliente_http.get("/servicos", headers=gerente)

    assert [s["nome"] for s in resposta.json()] == ["Alinhamento", "Troca de óleo"]


async def test_gerente_altera_preco_e_tempo_estimado(cliente_http, gerente):
    criado = (await _cadastrar(cliente_http, gerente)).json()

    resposta = await cliente_http.put(
        f"/servicos/{criado['id']}",
        json=TROCA_DE_OLEO | {"valor_base": "150.00", "tempo_estimado_minutos": 60},
        headers=gerente,
    )

    assert resposta.status_code == 200
    assert (resposta.json()["valor_base"], resposta.json()["tempo_estimado_minutos"]) == (
        "150.00",
        60,
    )


async def test_codigo_ja_cadastrado_responde_422(cliente_http, gerente):
    await _cadastrar(cliente_http, gerente)

    resposta = await _cadastrar(cliente_http, gerente, ALINHAMENTO | {"codigo": "SRV-001"})

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


@pytest.mark.parametrize(
    "alteracao",
    [{"valor_base": "-1.00"}, {"tempo_estimado_minutos": -5}, {"descricao": "   "}],
)
async def test_dados_invalidos_respondem_400(cliente_http, gerente, alteracao):
    resposta = await _cadastrar(cliente_http, gerente, TROCA_DE_OLEO | alteracao)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_servico_excluido_sai_do_catalogo_e_mantem_o_codigo_reservado(
    cliente_http, gerente, conexao
):
    criado = (await _cadastrar(cliente_http, gerente)).json()

    exclusao = await cliente_http.delete(f"/servicos/{criado['id']}", headers=gerente)

    assert exclusao.status_code == 204
    assert (await cliente_http.get("/servicos", headers=gerente)).json() == []
    detalhe = await cliente_http.get(f"/servicos/{criado['id']}", headers=gerente)
    assert detalhe.status_code == 404
    assert (
        await conexao.scalar(text("SELECT ativo FROM servicos WHERE codigo = 'SRV-001'")) is False
    )
    assert (await _cadastrar(cliente_http, gerente)).status_code == 422
