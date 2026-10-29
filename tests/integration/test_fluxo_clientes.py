"""Cadastro de clientes pelas rotas HTTP, com PostgreSQL real (RF-04 a RF-06, RNF-13)."""

import pytest
from sqlalchemy import text

MARIA = {
    "nome": "Maria Silva",
    "documento": "529.982.247-25",
    "email": "Maria@Exemplo.com",
    "telefone": "(11) 98765-4321",
}
EMPRESA = {
    "nome": "Auto Peças Ltda",
    "documento": "11.222.333/0001-81",
    "email": "contato@autopecas.com",
    "telefone": "1133334444",
}


async def _cadastrar(cliente_http, cabecalho, dados):
    return await cliente_http.post("/clientes", json=dados, headers=cabecalho)


async def test_atendente_cadastra_cliente_pessoa_fisica(cliente_http, atendente, conexao):
    resposta = await _cadastrar(cliente_http, atendente, MARIA)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["documento"] == "52998224725"
    assert corpo["tipo_documento"] == "CPF"
    assert corpo["email"] == "maria@exemplo.com"
    gravados = await conexao.scalar(
        text("SELECT count(*) FROM clientes WHERE documento = '52998224725' AND ativo")
    )
    assert gravados == 1


async def test_gerente_cadastra_cliente_pessoa_juridica(cliente_http, gerente):
    resposta = await _cadastrar(cliente_http, gerente, EMPRESA)

    assert resposta.status_code == 201
    assert resposta.json()["tipo_documento"] == "CNPJ"
    assert resposta.json()["documento"] == "11222333000181"


@pytest.mark.parametrize("documento", ["529.982.247-26", "11.222.333/0001-82", "123456"])
async def test_documento_invalido_responde_400(cliente_http, atendente, documento):
    resposta = await _cadastrar(cliente_http, atendente, MARIA | {"documento": documento})

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_documento_ja_cadastrado_responde_422(cliente_http, atendente):
    await _cadastrar(cliente_http, atendente, MARIA)

    resposta = await _cadastrar(
        cliente_http, atendente, MARIA | {"nome": "Outra", "documento": "52998224725"}
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_campo_ausente_responde_422_entrada_invalida(cliente_http, atendente):
    sem_telefone = {chave: valor for chave, valor in MARIA.items() if chave != "telefone"}

    resposta = await _cadastrar(cliente_http, atendente, sem_telefone)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"
    assert [d["campo"] for d in resposta.json()["detalhes"]] == ["body.telefone"]


async def test_mecanico_lista_e_detalha_mas_nao_cadastra(cliente_http, atendente, mecanico):
    criado = (await _cadastrar(cliente_http, atendente, MARIA)).json()

    assert (await _cadastrar(cliente_http, mecanico, EMPRESA)).status_code == 403
    lista = await cliente_http.get("/clientes", headers=mecanico)
    detalhe = await cliente_http.get(f"/clientes/{criado['id']}", headers=mecanico)

    assert lista.status_code == 200
    assert [c["id"] for c in lista.json()] == [criado["id"]]
    assert detalhe.json() == criado


async def test_listagem_em_ordem_de_nome(cliente_http, atendente):
    await _cadastrar(cliente_http, atendente, MARIA)
    await _cadastrar(cliente_http, atendente, EMPRESA)

    resposta = await cliente_http.get("/clientes", headers=atendente)

    assert [c["nome"] for c in resposta.json()] == ["Auto Peças Ltda", "Maria Silva"]


async def test_atualiza_os_dados_do_cliente(cliente_http, atendente):
    criado = (await _cadastrar(cliente_http, atendente, MARIA)).json()

    resposta = await cliente_http.put(
        f"/clientes/{criado['id']}",
        json=MARIA | {"nome": "Maria Souza", "telefone": "11911112222"},
        headers=atendente,
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Maria Souza"
    assert resposta.json()["telefone"] == "11911112222"


async def test_atualizar_para_documento_de_outro_cliente_responde_422(cliente_http, atendente):
    await _cadastrar(cliente_http, atendente, MARIA)
    empresa = (await _cadastrar(cliente_http, atendente, EMPRESA)).json()

    resposta = await cliente_http.put(
        f"/clientes/{empresa['id']}",
        json=EMPRESA | {"documento": MARIA["documento"]},
        headers=atendente,
    )

    assert resposta.status_code == 422


async def test_gerente_exclui_e_o_cliente_sai_do_cadastro(cliente_http, gerente, conexao):
    criado = (await _cadastrar(cliente_http, gerente, MARIA)).json()

    exclusao = await cliente_http.delete(f"/clientes/{criado['id']}", headers=gerente)

    assert exclusao.status_code == 204
    assert (await cliente_http.get("/clientes", headers=gerente)).json() == []
    detalhe = await cliente_http.get(f"/clientes/{criado['id']}", headers=gerente)
    assert detalhe.status_code == 404
    assert detalhe.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"
    ativo = await conexao.scalar(text("SELECT ativo FROM clientes WHERE documento = '52998224725'"))
    assert ativo is False


async def test_documento_de_cliente_excluido_continua_reservado(cliente_http, gerente):
    criado = (await _cadastrar(cliente_http, gerente, MARIA)).json()
    await cliente_http.delete(f"/clientes/{criado['id']}", headers=gerente)

    resposta = await _cadastrar(cliente_http, gerente, MARIA | {"nome": "Maria Nova"})

    assert resposta.status_code == 422


async def test_so_o_gerente_exclui(cliente_http, atendente, mecanico):
    criado = (await _cadastrar(cliente_http, atendente, MARIA)).json()

    for perfil in (atendente, mecanico):
        resposta = await cliente_http.delete(f"/clientes/{criado['id']}", headers=perfil)
        assert resposta.status_code == 403


async def test_sem_token_responde_401(cliente_http):
    assert (await cliente_http.get("/clientes")).status_code == 401
    assert (await cliente_http.post("/clientes", json=MARIA)).status_code == 401
