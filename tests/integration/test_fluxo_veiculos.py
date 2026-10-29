"""Cadastro de veículos pelas rotas HTTP, com PostgreSQL real (RF-07 a RF-09, RNF-13)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

MARIA = {
    "nome": "Maria Silva",
    "documento": "529.982.247-25",
    "email": "maria@exemplo.com",
    "telefone": "11987654321",
}
JOAO = {
    "nome": "João Souza",
    "documento": "111.444.777-35",
    "email": "joao@exemplo.com",
    "telefone": "11911112222",
}
UNO = {"placa": "abc-1d23", "marca": "Fiat", "modelo": "Uno", "ano": 2015}
GOL = {"placa": "XYZ9876", "marca": "VW", "modelo": "Gol", "ano": 2018}


async def _cadastrar_cliente(cliente_http, cabecalho, dados=MARIA) -> str:
    resposta = await cliente_http.post("/clientes", json=dados, headers=cabecalho)
    return resposta.json()["id"]


@pytest.fixture
async def maria_id(cliente_http, gerente) -> str:
    return await _cadastrar_cliente(cliente_http, gerente)


async def _cadastrar(cliente_http, cabecalho, cliente_id, dados=UNO):
    return await cliente_http.post(
        "/veiculos", json=dados | {"cliente_id": cliente_id}, headers=cabecalho
    )


async def test_atendente_cadastra_veiculo_com_placa_normalizada(
    cliente_http, atendente, maria_id, conexao
):
    resposta = await _cadastrar(cliente_http, atendente, maria_id)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["placa"] == "ABC1D23"
    assert corpo["cliente_id"] == maria_id
    gravados = await conexao.scalar(
        text("SELECT count(*) FROM veiculos WHERE placa = 'ABC1D23' AND ativo")
    )
    assert gravados == 1


@pytest.mark.parametrize("placa", ["ABC12345", "1BC1234", "ABC-1DD3"])
async def test_placa_invalida_responde_400(cliente_http, atendente, maria_id, placa):
    resposta = await _cadastrar(cliente_http, atendente, maria_id, UNO | {"placa": placa})

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_ano_fora_do_intervalo_responde_400(cliente_http, atendente, maria_id):
    resposta = await _cadastrar(cliente_http, atendente, maria_id, UNO | {"ano": 1899})

    assert resposta.status_code == 400


async def test_cliente_inexistente_responde_404(cliente_http, atendente):
    resposta = await _cadastrar(cliente_http, atendente, str(uuid4()))

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


async def test_cliente_excluido_responde_404(cliente_http, gerente, maria_id):
    await cliente_http.delete(f"/clientes/{maria_id}", headers=gerente)

    resposta = await _cadastrar(cliente_http, gerente, maria_id)

    assert resposta.status_code == 404


async def test_placa_de_outro_veiculo_ativo_responde_422(cliente_http, atendente, maria_id):
    await _cadastrar(cliente_http, atendente, maria_id)

    resposta = await _cadastrar(cliente_http, atendente, maria_id, GOL | {"placa": "ABC1D23"})

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_placa_de_veiculo_excluido_pode_ser_recadastrada(
    cliente_http, atendente, maria_id, conexao
):
    vendido = (await _cadastrar(cliente_http, atendente, maria_id)).json()
    await cliente_http.delete(f"/veiculos/{vendido['id']}", headers=atendente)
    joao_id = await _cadastrar_cliente(cliente_http, atendente, JOAO)

    resposta = await _cadastrar(cliente_http, atendente, joao_id)

    assert resposta.status_code == 201
    registros = await conexao.scalar(text("SELECT count(*) FROM veiculos WHERE placa = 'ABC1D23'"))
    assert registros == 2


async def test_campo_ausente_responde_422_entrada_invalida(cliente_http, atendente, maria_id):
    sem_ano = {chave: valor for chave, valor in UNO.items() if chave != "ano"}

    resposta = await _cadastrar(cliente_http, atendente, maria_id, sem_ano)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"


async def test_mecanico_lista_e_detalha_mas_nao_grava(cliente_http, atendente, mecanico, maria_id):
    criado = (await _cadastrar(cliente_http, atendente, maria_id)).json()

    assert (await _cadastrar(cliente_http, mecanico, maria_id, GOL)).status_code == 403
    atualizacao = await cliente_http.put(f"/veiculos/{criado['id']}", json=GOL, headers=mecanico)
    exclusao = await cliente_http.delete(f"/veiculos/{criado['id']}", headers=mecanico)
    lista = await cliente_http.get("/veiculos", headers=mecanico)
    detalhe = await cliente_http.get(f"/veiculos/{criado['id']}", headers=mecanico)

    assert (atualizacao.status_code, exclusao.status_code) == (403, 403)
    assert [v["id"] for v in lista.json()] == [criado["id"]]
    assert detalhe.json() == criado


async def test_listagem_filtra_pelo_cliente_em_ordem_de_placa(cliente_http, atendente, maria_id):
    joao_id = await _cadastrar_cliente(cliente_http, atendente, JOAO)
    await _cadastrar(cliente_http, atendente, maria_id, GOL)
    await _cadastrar(cliente_http, atendente, maria_id, UNO)
    await _cadastrar(cliente_http, atendente, joao_id, UNO | {"placa": "DEF5678"})

    todos = await cliente_http.get("/veiculos", headers=atendente)
    da_maria = await cliente_http.get(
        "/veiculos", params={"cliente_id": maria_id}, headers=atendente
    )
    de_ninguem = await cliente_http.get(
        "/veiculos", params={"cliente_id": str(uuid4())}, headers=atendente
    )

    assert [v["placa"] for v in todos.json()] == ["ABC1D23", "DEF5678", "XYZ9876"]
    assert [v["placa"] for v in da_maria.json()] == ["ABC1D23", "XYZ9876"]
    assert de_ninguem.status_code == 200
    assert de_ninguem.json() == []


async def test_atualiza_os_dados_e_mantem_o_proprietario(cliente_http, atendente, maria_id):
    criado = (await _cadastrar(cliente_http, atendente, maria_id)).json()

    resposta = await cliente_http.put(f"/veiculos/{criado['id']}", json=GOL, headers=atendente)

    assert resposta.status_code == 200
    assert resposta.json() == GOL | {"id": criado["id"], "cliente_id": maria_id}


async def test_atualizar_para_placa_de_outro_veiculo_responde_422(
    cliente_http, atendente, maria_id
):
    await _cadastrar(cliente_http, atendente, maria_id, GOL)
    uno = (await _cadastrar(cliente_http, atendente, maria_id)).json()

    resposta = await cliente_http.put(
        f"/veiculos/{uno['id']}", json=UNO | {"placa": GOL["placa"]}, headers=atendente
    )

    assert resposta.status_code == 422


@pytest.mark.parametrize("perfil", ["atendente", "gerente"])
async def test_atendente_e_gerente_excluem(cliente_http, maria_id, conexao, request, perfil):
    cabecalho = request.getfixturevalue(perfil)
    criado = (await _cadastrar(cliente_http, cabecalho, maria_id)).json()

    exclusao = await cliente_http.delete(f"/veiculos/{criado['id']}", headers=cabecalho)

    assert exclusao.status_code == 204
    assert (await cliente_http.get("/veiculos", headers=cabecalho)).json() == []
    detalhe = await cliente_http.get(f"/veiculos/{criado['id']}", headers=cabecalho)
    assert detalhe.status_code == 404
    ativo = await conexao.scalar(text("SELECT ativo FROM veiculos WHERE placa = 'ABC1D23'"))
    assert ativo is False


async def test_excluir_o_cliente_exclui_os_veiculos_dele(cliente_http, gerente, maria_id, conexao):
    joao_id = await _cadastrar_cliente(cliente_http, gerente, JOAO)
    await _cadastrar(cliente_http, gerente, maria_id, UNO)
    await _cadastrar(cliente_http, gerente, maria_id, GOL)
    do_joao = (await _cadastrar(cliente_http, gerente, joao_id, UNO | {"placa": "DEF5678"})).json()

    exclusao = await cliente_http.delete(f"/clientes/{maria_id}", headers=gerente)

    assert exclusao.status_code == 204
    restantes = (await cliente_http.get("/veiculos", headers=gerente)).json()
    assert [v["id"] for v in restantes] == [do_joao["id"]]
    ativos_da_maria = await conexao.scalar(
        text("SELECT count(*) FROM veiculos WHERE cliente_id = :id AND ativo"),
        {"id": UUID(maria_id)},
    )
    assert ativos_da_maria == 0
