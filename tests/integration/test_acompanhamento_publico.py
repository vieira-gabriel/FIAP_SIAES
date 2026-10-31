"""Consulta, aprovação e rejeição do orçamento pelo cliente, pelo número da OS e pelo CPF/CNPJ,
sem JWT, com PostgreSQL real (RF-25, RF-26, RF-18)."""

from uuid import uuid4

import pytest
from asyncpg.exceptions import DeadlockDetectedError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.repositories.postgres_estoque_repository import PostgresEstoqueRepository
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


async def _aprovar(cliente_http, numero: str, documento: str = DOCUMENTO):
    corpo = {"numero": numero, "documento": documento}
    return await cliente_http.post("/acompanhamento/aprovacao", json=corpo)


async def _detalhe(cliente_http, quem, os_id: str) -> dict:
    return (await cliente_http.get(f"/ordens-servico/{os_id}", headers=_cabecalho(quem))).json()


async def test_aprovacao_com_peca_pendente_aguarda_a_peca(cliente_http, gerente, os_orcada):
    resposta = await _aprovar(cliente_http, os_orcada["numero"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "AGUARDANDO_PECA"
    assert corpo["pecas_pendentes"] == [{"nome": "Filtro de óleo", "quantidade": 2}]
    registro = (await _detalhe(cliente_http, gerente, os_orcada["id"]))["historico"][-1]
    assert (registro["status_anterior"], registro["status_novo"]) == (
        "AGUARDANDO_APROVACAO",
        "AGUARDANDO_PECA",
    )
    assert (registro["origem"], registro["usuario_id"]) == ("CLIENTE", None)


async def test_aprovacao_sem_peca_pendente_aguarda_a_execucao(
    cliente_http, mecanico, gerente, os_recebida
):
    await _orcar(cliente_http, mecanico, gerente, os_recebida, saldo=5)

    resposta = await _aprovar(cliente_http, os_recebida["numero"])

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "AGUARDANDO_EXECUCAO"
    assert resposta.json()["pecas_pendentes"] == []
    registro = (await _detalhe(cliente_http, gerente, os_recebida["id"]))["historico"][-1]
    assert (registro["status_novo"], registro["origem"]) == ("AGUARDANDO_EXECUCAO", "CLIENTE")


async def test_reposicao_libera_a_os_aprovada_com_peca_pendente(
    cliente_http, mecanico, gerente, os_orcada
):
    await _aprovar(cliente_http, os_orcada["numero"])
    (peca,) = (await _detalhe(cliente_http, gerente, os_orcada["id"]))["pecas"]

    reposicao = await cliente_http.post(
        f"/pecas/{peca['peca_id']}/reposicao",
        json={"quantidade": 2},
        headers=_cabecalho(mecanico),
    )

    assert reposicao.status_code == 200
    assert (await _detalhe(cliente_http, gerente, os_orcada["id"]))["status"] == (
        "AGUARDANDO_EXECUCAO"
    )


async def test_segunda_aprovacao_responde_422(cliente_http, os_orcada):
    primeira = await _aprovar(cliente_http, os_orcada["numero"])
    segunda = await _aprovar(cliente_http, os_orcada["numero"])

    assert (primeira.status_code, segunda.status_code) == (200, 422)
    assert segunda.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_aprovacao_de_os_ainda_sem_orcamento_responde_422(cliente_http, os_recebida):
    resposta = await _aprovar(cliente_http, os_recebida["numero"])

    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "REGRA_DE_NEGOCIO_VIOLADA")


async def test_aprovacao_com_identificacao_errada_responde_404_e_nao_aprova(
    cliente_http, gerente, os_orcada
):
    inexistente = await _aprovar(cliente_http, "999-00000000")
    outro_titular = await _aprovar(cliente_http, os_orcada["numero"], "111.444.777-35")

    assert inexistente.status_code == outro_titular.status_code == 404
    assert inexistente.json() == outro_titular.json()
    assert (await _detalhe(cliente_http, gerente, os_orcada["id"]))["status"] == (
        "AGUARDANDO_APROVACAO"
    )


async def _rejeitar(cliente_http, numero: str, documento: str = DOCUMENTO):
    corpo = {"numero": numero, "documento": documento}
    return await cliente_http.post("/acompanhamento/rejeicao", json=corpo)


async def _estoque(cliente_http, quem, peca_id: str) -> tuple[int, int, int]:
    corpo = (await cliente_http.get(f"/pecas/{peca_id}", headers=_cabecalho(quem))).json()
    return corpo["quantidade_fisica"], corpo["quantidade_reservada"], corpo["saldo_disponivel"]


async def _peca_da_os(cliente_http, quem, os_id: str) -> str:
    (peca,) = (await _detalhe(cliente_http, quem, os_id))["pecas"]
    return peca["peca_id"]


async def test_rejeicao_cancela_a_os_e_devolve_as_reservas_ao_saldo_disponivel(
    cliente_http, mecanico, gerente, os_recebida
):
    await _orcar(cliente_http, mecanico, gerente, os_recebida, saldo=5)
    peca_id = await _peca_da_os(cliente_http, gerente, os_recebida["id"])
    assert await _estoque(cliente_http, gerente, peca_id) == (5, 2, 3)

    resposta = await _rejeitar(cliente_http, os_recebida["numero"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["status"], corpo["estimativa_entrega"]) == ("CANCELADA", None)
    assert await _estoque(cliente_http, gerente, peca_id) == (5, 0, 5)
    registro = (await _detalhe(cliente_http, gerente, os_recebida["id"]))["historico"][-1]
    assert (registro["status_anterior"], registro["status_novo"]) == (
        "AGUARDANDO_APROVACAO",
        "CANCELADA",
    )
    assert (registro["origem"], registro["usuario_id"]) == ("CLIENTE", None)


async def test_rejeicao_com_peca_pendente_remove_a_pendencia(
    cliente_http, mecanico, gerente, os_orcada
):
    peca_id = await _peca_da_os(cliente_http, gerente, os_orcada["id"])

    resposta = await _rejeitar(cliente_http, os_orcada["numero"])
    reposicao = await cliente_http.post(
        f"/pecas/{peca_id}/reposicao", json={"quantidade": 2}, headers=_cabecalho(mecanico)
    )

    assert resposta.status_code == 200
    assert reposicao.status_code == 200
    assert await _estoque(cliente_http, gerente, peca_id) == (2, 0, 2)
    assert (await _detalhe(cliente_http, gerente, os_orcada["id"]))["status"] == "CANCELADA"


async def test_saldo_devolvido_pela_rejeicao_libera_a_os_que_esperava_a_peca(
    cliente_http, atendente, mecanico, gerente, os_recebida, conexao
):
    await _orcar(cliente_http, mecanico, gerente, os_recebida, saldo=2)
    peca_id = await _peca_da_os(cliente_http, gerente, os_recebida["id"])
    outro = await cliente_http.post(
        "/ordens-servico",
        json=ABERTURA
        | {"placa": "XYZ9K88", "documento": "111.444.777-35"}
        | {"cliente": {"nome": "João", "email": "joao@exemplo.com", "telefone": "11911112222"}},
        headers=_cabecalho(atendente),
    )
    esperando_id = outro.json()["id"]
    await cliente_http.post(
        f"/ordens-servico/{esperando_id}/mecanico", headers=_cabecalho(mecanico)
    )
    await cliente_http.post(
        f"/ordens-servico/{esperando_id}/pecas",
        json={"peca_id": peca_id, "quantidade": 2},
        headers=_cabecalho(mecanico),
    )
    await cliente_http.post(
        f"/ordens-servico/{esperando_id}/orcamento", headers=_cabecalho(mecanico)
    )
    assert await _estoque(cliente_http, gerente, peca_id) == (2, 2, 0)

    await _rejeitar(cliente_http, os_recebida["numero"])

    esperando = await _detalhe(cliente_http, gerente, esperando_id)
    assert esperando["pecas"][0]["quantidade_reservada"] == 2
    assert await _estoque(cliente_http, gerente, peca_id) == (2, 2, 0)


async def test_segunda_rejeicao_responde_422(cliente_http, os_orcada):
    primeira = await _rejeitar(cliente_http, os_orcada["numero"])
    segunda = await _rejeitar(cliente_http, os_orcada["numero"])

    assert (primeira.status_code, segunda.status_code) == (200, 422)
    assert segunda.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_rejeicao_depois_da_aprovacao_responde_422_e_mantem_as_reservas(
    cliente_http, mecanico, gerente, os_recebida
):
    await _orcar(cliente_http, mecanico, gerente, os_recebida, saldo=5)
    peca_id = await _peca_da_os(cliente_http, gerente, os_recebida["id"])
    await _aprovar(cliente_http, os_recebida["numero"])

    resposta = await _rejeitar(cliente_http, os_recebida["numero"])

    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "REGRA_DE_NEGOCIO_VIOLADA")
    assert await _estoque(cliente_http, gerente, peca_id) == (5, 2, 3)


async def test_rejeicao_de_os_ainda_sem_orcamento_responde_422(cliente_http, os_recebida):
    resposta = await _rejeitar(cliente_http, os_recebida["numero"])

    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "REGRA_DE_NEGOCIO_VIOLADA")


async def test_rejeicao_com_identificacao_errada_responde_404_e_nao_cancela(
    cliente_http, gerente, os_orcada
):
    inexistente = await _rejeitar(cliente_http, "999-00000000")
    outro_titular = await _rejeitar(cliente_http, os_orcada["numero"], "111.444.777-35")

    assert inexistente.status_code == outro_titular.status_code == 404
    assert inexistente.json() == outro_titular.json()
    assert (await _detalhe(cliente_http, gerente, os_orcada["id"]))["status"] == (
        "AGUARDANDO_APROVACAO"
    )


async def test_impasse_na_rejeicao_e_repetido_e_a_resposta_e_200(
    cliente_http, mecanico, gerente, os_recebida, monkeypatch
):
    await _orcar(cliente_http, mecanico, gerente, os_recebida, saldo=5)
    peca_id = await _peca_da_os(cliente_http, gerente, os_recebida["id"])
    salvar_original = PostgresEstoqueRepository.salvar
    tentativas = []

    async def salvar_com_impasse_na_primeira_vez(self, estoque):
        tentativas.append(estoque.peca_id)
        if len(tentativas) == 1:
            raise DBAPIError("UPDATE estoque_pecas", None, DeadlockDetectedError())
        await salvar_original(self, estoque)

    monkeypatch.setattr(PostgresEstoqueRepository, "salvar", salvar_com_impasse_na_primeira_vez)

    resposta = await _rejeitar(cliente_http, os_recebida["numero"])

    assert resposta.status_code == 200
    assert len(tentativas) == 2
    assert await _estoque(cliente_http, gerente, peca_id) == (5, 0, 5)
