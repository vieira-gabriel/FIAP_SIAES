"""Consulta pública da OS pelo número e pelo CPF/CNPJ, sem JWT, com PostgreSQL real (RF-25)."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

DOCUMENTO = "529.982.247-25"
ABERTURA = {
    "documento": DOCUMENTO,
    "placa": "ABC1D23",
    "cliente": {"nome": "Maria Silva", "email": "maria@exemplo.com", "telefone": "11987654321"},
    "veiculo": {"marca": "Fiat", "modelo": "Uno", "ano": 2015},
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
    "quantidade_fisica_inicial": 0,
}


async def _inserir_usuario(conexao, perfil: PerfilUsuario) -> Usuario:
    usuario = Usuario(
        nome=perfil.value.title(),
        email=f"{perfil.value.lower()}-{uuid4().hex[:8]}@oficina.com",
        senha_hash="hash",
        perfil=perfil,
    )
    await conexao.execute(
        text(
            "INSERT INTO usuarios (id, nome, email, senha_hash, perfil, ativo) "
            "VALUES (:id, :nome, :email, :senha_hash, :perfil, true)"
        ),
        {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "senha_hash": usuario.senha_hash,
            "perfil": perfil.value,
        },
    )
    return usuario


def _cabecalho(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.state.token_service.emitir(usuario)}"}


@pytest.fixture
async def atendente(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.ATENDENTE)


@pytest.fixture
async def mecanico(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.MECANICO)


@pytest.fixture
async def gerente(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.GERENTE)


@pytest.fixture
async def os_recebida(cliente_http, atendente) -> dict:
    resposta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    assert resposta.status_code == 201
    return resposta.json()


async def _orcar(cliente_http, mecanico, gerente, os_recebida, saldo: int) -> dict:
    """Um serviço de 45 minutos e 2 peças (3 dias de reposição), com orçamento concluído."""
    servico = await cliente_http.post("/servicos", json=SERVICO, headers=_cabecalho(gerente))
    peca = await cliente_http.post(
        "/pecas", json=PECA | {"quantidade_fisica_inicial": saldo}, headers=_cabecalho(gerente)
    )
    os_id = os_recebida["id"]
    await cliente_http.post(f"/ordens-servico/{os_id}/mecanico", headers=_cabecalho(mecanico))
    await cliente_http.post(
        f"/ordens-servico/{os_id}/servicos",
        json={"servico_id": servico.json()["id"]},
        headers=_cabecalho(mecanico),
    )
    await cliente_http.post(
        f"/ordens-servico/{os_id}/pecas",
        json={"peca_id": peca.json()["id"], "quantidade": 2},
        headers=_cabecalho(mecanico),
    )
    resposta = await cliente_http.post(
        f"/ordens-servico/{os_id}/orcamento", headers=_cabecalho(mecanico)
    )
    assert resposta.status_code == 200
    return os_recebida


@pytest.fixture
async def os_orcada(cliente_http, mecanico, gerente, os_recebida) -> dict:
    return await _orcar(cliente_http, mecanico, gerente, os_recebida, saldo=0)


async def _consultar(cliente_http, numero: str, documento: str = DOCUMENTO):
    return await cliente_http.post(
        "/acompanhamento", json={"numero": numero, "documento": documento}
    )


async def test_consulta_com_numero_e_documento_corretos_sem_token(cliente_http, os_orcada):
    resposta = await _consultar(cliente_http, os_orcada["numero"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["numero"] == os_orcada["numero"]
    assert corpo["status"] == "AGUARDANDO_APROVACAO"
    assert corpo["servicos"] == ["Troca de óleo"]
    assert corpo["pecas_pendentes"] == [{"nome": "Filtro de óleo", "quantidade": 2}]
    assert corpo["valor_total"] == "191.80"
    assert corpo["estimativa_entrega"] is not None


async def test_peca_reservada_nao_aparece_entre_as_pendentes(
    cliente_http, mecanico, gerente, os_recebida
):
    await _orcar(cliente_http, mecanico, gerente, os_recebida, saldo=5)

    corpo = (await _consultar(cliente_http, os_recebida["numero"])).json()

    assert corpo["pecas_pendentes"] == []
    assert corpo["valor_total"] == "191.80"


async def test_os_recebida_nao_tem_estimativa_nem_valor(cliente_http, os_recebida):
    resposta = await _consultar(cliente_http, os_recebida["numero"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["status"], corpo["valor_total"], corpo["estimativa_entrega"]) == (
        "RECEBIDA",
        None,
        None,
    )
    assert (corpo["servicos"], corpo["pecas_pendentes"]) == ([], [])


@pytest.mark.parametrize("documento", ["52998224725", " 529.982.247-25"])
async def test_documento_com_ou_sem_pontuacao(cliente_http, os_recebida, documento):
    resposta = await _consultar(cliente_http, os_recebida["numero"], documento)

    assert resposta.status_code == 200


async def test_numero_em_minusculas(cliente_http, os_recebida):
    resposta = await _consultar(cliente_http, os_recebida["numero"].lower())

    assert resposta.status_code == 200


async def test_numero_inexistente_e_documento_errado_respondem_igual(cliente_http, os_recebida):
    inexistente = await _consultar(cliente_http, "999-00000000")
    documento_errado = await _consultar(cliente_http, os_recebida["numero"], "111.444.777-35")

    assert inexistente.status_code == documento_errado.status_code == 404
    assert inexistente.json() == documento_errado.json()
    assert inexistente.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


@pytest.mark.parametrize(
    ("numero", "documento"),
    [("sem formato", DOCUMENTO), ("PLACEHOLDER", "123"), ("PLACEHOLDER", "529.982.247-26")],
    ids=["numero malformado", "documento curto", "documento com digito invalido"],
)
async def test_valores_malformados_respondem_como_nao_encontrada(
    cliente_http, os_recebida, numero, documento
):
    numero = os_recebida["numero"] if numero == "PLACEHOLDER" else numero
    referencia = await _consultar(cliente_http, "999-00000000")

    resposta = await _consultar(cliente_http, numero, documento)

    assert (resposta.status_code, resposta.json()) == (404, referencia.json())


@pytest.mark.parametrize("corpo", [{}, {"numero": "529-7F3A9C2B"}, {"documento": DOCUMENTO}])
async def test_corpo_incompleto_responde_422(cliente_http, corpo):
    resposta = await cliente_http.post("/acompanhamento", json=corpo)

    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "ENTRADA_INVALIDA")


async def test_resposta_nao_expoe_dados_pessoais_nem_custos(cliente_http, os_orcada):
    resposta = await _consultar(cliente_http, os_orcada["numero"])

    assert set(resposta.json()) == {
        "numero",
        "status",
        "servicos",
        "pecas_pendentes",
        "valor_total",
        "estimativa_entrega",
    }
    corpo = resposta.text
    for dado in (
        "maria@exemplo.com",
        "11987654321",
        "Maria",
        "52998224725",
        "529.982.247",
        "ABC1D23",
    ):
        assert dado not in corpo
    for custo in ("35.90", "71.80", "120.00", "preco"):
        assert custo not in corpo


async def test_cliente_excluido_continua_consultando_a_os(
    cliente_http, gerente, os_recebida, conexao
):
    await conexao.execute(text("UPDATE clientes SET ativo = false"))

    resposta = await _consultar(cliente_http, os_recebida["numero"])

    assert resposta.status_code == 200
