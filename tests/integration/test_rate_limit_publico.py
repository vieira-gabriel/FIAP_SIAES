"""Limite de requisições por IP nas rotas públicas, com a aplicação real (RNF-05)."""

import pytest

from presentation.middlewares.rate_limit import configurar_limite_publico

CONSULTA = {"numero": "999-00000000", "documento": "529.982.247-25"}


async def _consultar(cliente_http):
    return await cliente_http.post("/acompanhamento", json=CONSULTA)


async def test_a_11a_requisicao_no_mesmo_minuto_recebe_429(cliente_http):
    respostas = [await _consultar(cliente_http) for _ in range(11)]

    assert [r.status_code for r in respostas[:10]] == [404] * 10
    estouro = respostas[10]
    assert estouro.status_code == 429
    assert estouro.json() == {
        "codigo": "LIMITE_DE_REQUISICOES_EXCEDIDO",
        "mensagem": "Muitas requisições. Tente novamente em instantes.",
        "detalhes": [],
    }
    assert estouro.headers["Retry-After"] == "60"


async def test_consulta_aprovacao_e_rejeicao_dividem_o_mesmo_contador(cliente_http):
    for _ in range(4):
        await _consultar(cliente_http)
    for _ in range(3):
        await cliente_http.post("/acompanhamento/aprovacao", json=CONSULTA)
    for _ in range(3):
        await cliente_http.post("/acompanhamento/rejeicao", json=CONSULTA)

    assert (await _consultar(cliente_http)).status_code == 429
    assert (await cliente_http.post("/acompanhamento/aprovacao", json=CONSULTA)).status_code == 429
    assert (await cliente_http.post("/acompanhamento/rejeicao", json=CONSULTA)).status_code == 429


async def test_o_limite_vem_da_configuracao(cliente_http):
    configurar_limite_publico("2/minute")

    respostas = [await _consultar(cliente_http) for _ in range(3)]

    assert [r.status_code for r in respostas] == [404, 404, 429]


async def test_corpo_fora_do_dto_responde_422_antes_do_limite_e_nao_conta(cliente_http):
    respostas = [await cliente_http.post("/acompanhamento", json={}) for _ in range(12)]

    assert {r.status_code for r in respostas} == {422}
    assert (await _consultar(cliente_http)).status_code == 404


async def test_consulta_com_documento_malformado_conta_para_o_limite(cliente_http):
    corpo = CONSULTA | {"documento": "123"}
    for _ in range(10):
        assert (await cliente_http.post("/acompanhamento", json=corpo)).status_code == 404

    assert (await _consultar(cliente_http)).status_code == 429


async def test_rota_autenticada_nao_tem_limite(cliente_http, gerente):
    respostas = [await cliente_http.get("/ordens-servico", headers=gerente) for _ in range(15)]

    assert {r.status_code for r in respostas} == {200}


async def test_login_nao_tem_limite_publico(cliente_http):
    credenciais = {"email": "ninguem@oficina.com", "senha": "senha-errada-123"}

    respostas = [await cliente_http.post("/auth/login", json=credenciais) for _ in range(12)]

    assert 429 not in {r.status_code for r in respostas}


async def test_a_nova_subida_zera_os_contadores(cliente_http):
    for _ in range(10):
        await _consultar(cliente_http)
    assert (await _consultar(cliente_http)).status_code == 429

    configurar_limite_publico("10/minute")

    assert (await _consultar(cliente_http)).status_code == 404


@pytest.mark.parametrize("limite", ["", "dez por minuto", "10"])
def test_limite_malformado_e_recusado_na_subida(limite):
    with pytest.raises(ValueError):
        configurar_limite_publico(limite)
