"""Peças e estoque pelas rotas HTTP, com PostgreSQL real (RF-12, RNF-13)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_cliente_repository import PostgresClienteRepository
from infrastructure.repositories.postgres_ordem_servico_repository import (
    PostgresOrdemServicoRepository,
)
from infrastructure.repositories.postgres_peca_repository import PostgresPecaRepository
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.repositories.postgres_veiculo_repository import PostgresVeiculoRepository

FILTRO = {
    "codigo_referencia": "FLT-001",
    "nome": "Filtro de óleo",
    "preco_unitario": "35.90",
    "prazo_reposicao_dias": 3,
}
VELA = {
    "codigo_referencia": "VEL-001",
    "nome": "Vela de ignição",
    "preco_unitario": "20.00",
    "prazo_reposicao_dias": 2,
}


async def _cadastrar(cliente_http, cabecalho, dados=FILTRO):
    return await cliente_http.post("/pecas", json=dados, headers=cabecalho)


async def _reservar(conexao, peca_id, quantidade):
    await conexao.execute(
        text("UPDATE estoque_pecas SET quantidade_reservada = :q WHERE peca_id = :id"),
        {"q": quantidade, "id": peca_id},
    )


async def test_gerente_cadastra_peca_com_quantidade_inicial(cliente_http, gerente, conexao):
    resposta = await _cadastrar(cliente_http, gerente, FILTRO | {"quantidade_fisica_inicial": 10})

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert (corpo["preco_unitario"], corpo["quantidade_fisica"], corpo["saldo_disponivel"]) == (
        "35.90",
        10,
        10,
    )
    gravado = await conexao.scalar(
        text("SELECT quantidade_fisica FROM estoque_pecas WHERE peca_id = :id"),
        {"id": corpo["id"]},
    )
    assert gravado == 10


@pytest.mark.parametrize("perfil", ["atendente", "mecanico", "gerente"])
async def test_todos_os_perfis_consultam_as_pecas(cliente_http, gerente, perfil, request):
    criada = (await _cadastrar(cliente_http, gerente)).json()
    cabecalho = request.getfixturevalue(perfil)

    lista = await cliente_http.get("/pecas", headers=cabecalho)
    detalhe = await cliente_http.get(f"/pecas/{criada['id']}", headers=cabecalho)

    assert lista.json() == [criada]
    assert detalhe.json() == criada


async def test_listagem_em_ordem_de_nome(cliente_http, gerente):
    await _cadastrar(cliente_http, gerente, VELA)
    await _cadastrar(cliente_http, gerente, FILTRO)

    resposta = await cliente_http.get("/pecas", headers=gerente)

    assert [p["nome"] for p in resposta.json()] == ["Filtro de óleo", "Vela de ignição"]


@pytest.mark.parametrize("perfil", ["mecanico", "gerente"])
async def test_mecanico_e_gerente_movimentam_o_estoque(cliente_http, gerente, perfil, request):
    criada = (await _cadastrar(cliente_http, gerente)).json()
    cabecalho = request.getfixturevalue(perfil)

    reposicao = await cliente_http.post(
        f"/pecas/{criada['id']}/reposicao", json={"quantidade": 5}, headers=cabecalho
    )
    ajuste = await cliente_http.put(
        f"/pecas/{criada['id']}/quantidade-fisica", json={"quantidade_fisica": 3}, headers=cabecalho
    )

    assert (reposicao.status_code, reposicao.json()["quantidade_fisica"]) == (200, 5)
    assert (ajuste.status_code, ajuste.json()["saldo_disponivel"]) == (200, 3)


async def test_ajuste_abaixo_da_reserva_responde_422(cliente_http, gerente, conexao):
    criada = (
        await _cadastrar(cliente_http, gerente, FILTRO | {"quantidade_fisica_inicial": 5})
    ).json()
    await _reservar(conexao, criada["id"], 3)

    resposta = await cliente_http.put(
        f"/pecas/{criada['id']}/quantidade-fisica", json={"quantidade_fisica": 2}, headers=gerente
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_reposicao_nao_positiva_responde_400(cliente_http, gerente):
    criada = (await _cadastrar(cliente_http, gerente)).json()

    resposta = await cliente_http.post(
        f"/pecas/{criada['id']}/reposicao", json={"quantidade": 0}, headers=gerente
    )

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_peca_excluida_sai_da_listagem_e_mantem_as_reservas(cliente_http, gerente, conexao):
    criada = (
        await _cadastrar(cliente_http, gerente, FILTRO | {"quantidade_fisica_inicial": 5})
    ).json()
    await _reservar(conexao, criada["id"], 2)

    exclusao = await cliente_http.delete(f"/pecas/{criada['id']}", headers=gerente)

    assert exclusao.status_code == 204
    assert (await cliente_http.get("/pecas", headers=gerente)).json() == []
    reservada = await conexao.scalar(
        text("SELECT quantidade_reservada FROM estoque_pecas WHERE peca_id = :id"),
        {"id": criada["id"]},
    )
    assert reservada == 2


async def test_peca_excluida_nao_e_encontrada_e_mantem_o_codigo_reservado(cliente_http, gerente):
    criada = (await _cadastrar(cliente_http, gerente)).json()
    await cliente_http.delete(f"/pecas/{criada['id']}", headers=gerente)
    url = f"/pecas/{criada['id']}"

    respostas = [
        await cliente_http.get(url, headers=gerente),
        await cliente_http.put(url, json=FILTRO, headers=gerente),
        await cliente_http.delete(url, headers=gerente),
        await cliente_http.post(f"{url}/reposicao", json={"quantidade": 1}, headers=gerente),
        await cliente_http.put(
            f"{url}/quantidade-fisica", json={"quantidade_fisica": 1}, headers=gerente
        ),
    ]

    assert [r.status_code for r in respostas] == [404] * 5
    assert (await _cadastrar(cliente_http, gerente)).status_code == 422


async def test_codigo_ja_cadastrado_responde_422(cliente_http, gerente):
    await _cadastrar(cliente_http, gerente)

    resposta = await _cadastrar(cliente_http, gerente, VELA | {"codigo_referencia": "FLT-001"})

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_peca_inexistente_responde_404(cliente_http, gerente):
    resposta = await cliente_http.get(f"/pecas/{uuid4()}", headers=gerente)

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


@pytest.mark.parametrize(
    "alteracao",
    [{"preco_unitario": "-1.00"}, {"prazo_reposicao_dias": -1}, {"nome": "   "}],
)
async def test_dados_invalidos_respondem_400(cliente_http, gerente, alteracao):
    resposta = await _cadastrar(cliente_http, gerente, FILTRO | alteracao)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


@pytest.mark.parametrize(
    "alteracao",
    [
        {"preco_unitario": "10000000000.00"},
        {"prazo_reposicao_dias": 2_147_483_648},
        {"quantidade_fisica_inicial": 2_147_483_648},
        {"prazo_reposicao_dias": "três"},
    ],
)
async def test_valor_fora_do_formato_ou_da_faixa_do_banco_responde_422(
    cliente_http, gerente, alteracao
):
    resposta = await _cadastrar(cliente_http, gerente, FILTRO | alteracao)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"


async def test_corpo_sem_campo_obrigatorio_responde_422(cliente_http, gerente):
    criada = (await _cadastrar(cliente_http, gerente)).json()

    resposta = await cliente_http.post(f"/pecas/{criada['id']}/reposicao", json={}, headers=gerente)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"


async def _abrir_os_com_a_peca_pendente(fabrica_de_sessoes, peca_id):
    atendente = Usuario(
        nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=PerfilUsuario.ATENDENTE
    )
    cliente = Cliente(
        nome="Carla", documento=CPF("529.982.247-25"), email="c@email.com", telefone="1199999"
    )
    veiculo = Veiculo(
        cliente_id=cliente.id, placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2020
    )
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        sessao = unidade.sessao
        await PostgresUsuarioRepository(sessao).salvar(atendente)
        await PostgresClienteRepository(sessao).salvar(cliente)
        await sessao.flush()
        await PostgresVeiculoRepository(sessao).salvar(veiculo)
        await sessao.flush()
        peca = await PostgresPecaRepository(sessao).buscar_por_id(peca_id)
        os = OrdemServico.abrir(
            numero=NumeroOS("529-7F3A9C2B"),
            cliente_id=cliente.id,
            veiculo_id=veiculo.id,
            atendente_id=atendente.id,
        )
        os.atribuir_mecanico(atendente.id)
        os.incluir_peca(peca, quantidade=1)
        os.finalizar_orcamento(atendente.id, [], [peca])
        await PostgresOrdemServicoRepository(sessao).salvar(os)


async def test_peca_pendente_em_alguma_os_nao_e_excluida(cliente_http, gerente, fabrica_de_sessoes):
    criada = (await _cadastrar(cliente_http, gerente)).json()
    await _abrir_os_com_a_peca_pendente(fabrica_de_sessoes, UUID(criada["id"]))

    resposta = await cliente_http.delete(f"/pecas/{criada['id']}", headers=gerente)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"
    assert "529-7F3A9C2B" in resposta.json()["mensagem"]
    assert (await cliente_http.get(f"/pecas/{criada['id']}", headers=gerente)).status_code == 200
