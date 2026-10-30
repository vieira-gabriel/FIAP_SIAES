"""Itens da OS e conclusão do orçamento pela rota HTTP, com PostgreSQL real (RF-17, RNF-08, RNF-11,
RNF-13)."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from application.events.event_dispatcher import EventHandler
from domain.entities.usuario import Usuario
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

ABERTURA = {
    "documento": "529.982.247-25",
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
}
MAIOR_INTEIRO = 2_147_483_647


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
async def servico(cliente_http, gerente) -> dict:
    resposta = await cliente_http.post("/servicos", json=SERVICO, headers=_cabecalho(gerente))
    assert resposta.status_code == 201
    return resposta.json()


@pytest.fixture
async def peca(cliente_http, gerente) -> dict:
    resposta = await cliente_http.post(
        "/pecas", json=PECA | {"quantidade_fisica_inicial": 0}, headers=_cabecalho(gerente)
    )
    assert resposta.status_code == 201
    return resposta.json()


@pytest.fixture
async def os_recebida(cliente_http, atendente) -> dict:
    resposta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    assert resposta.status_code == 201
    return resposta.json()


@pytest.fixture
async def os_em_diagnostico(cliente_http, mecanico, os_recebida) -> dict:
    resposta = await cliente_http.post(
        f"/ordens-servico/{os_recebida['id']}/mecanico", headers=_cabecalho(mecanico)
    )
    assert resposta.status_code == 200
    return os_recebida


async def _incluir_servico(cliente_http, quem, os_id, servico_id):
    return await cliente_http.post(
        f"/ordens-servico/{os_id}/servicos",
        json={"servico_id": servico_id},
        headers=_cabecalho(quem),
    )


async def _incluir_peca(cliente_http, quem, os_id, peca_id, quantidade=2):
    return await cliente_http.post(
        f"/ordens-servico/{os_id}/pecas",
        json={"peca_id": peca_id, "quantidade": quantidade},
        headers=_cabecalho(quem),
    )


async def _concluir(cliente_http, quem, os_id):
    return await cliente_http.post(f"/ordens-servico/{os_id}/orcamento", headers=_cabecalho(quem))


async def _detalhe(cliente_http, quem, os_id) -> dict:
    return (await cliente_http.get(f"/ordens-servico/{os_id}", headers=_cabecalho(quem))).json()


async def _os_com_itens(cliente_http, mecanico, os, servico, peca) -> None:
    assert (
        await _incluir_servico(cliente_http, mecanico, os["id"], servico["id"])
    ).status_code == 201
    assert (await _incluir_peca(cliente_http, mecanico, os["id"], peca["id"])).status_code == 201


async def test_inclui_servico_e_peca_e_mostra_os_itens_sem_orcamento(
    cliente_http, mecanico, os_em_diagnostico, servico, peca
):
    resposta_servico = await _incluir_servico(
        cliente_http, mecanico, os_em_diagnostico["id"], servico["id"]
    )
    resposta_peca = await _incluir_peca(cliente_http, mecanico, os_em_diagnostico["id"], peca["id"])

    assert resposta_servico.status_code == 201
    assert resposta_peca.status_code == 201
    corpo = resposta_peca.json()
    assert corpo["status"] == "EM_DIAGNOSTICO"
    assert corpo["orcamento"] is None
    assert [s["preco_congelado"] for s in corpo["servicos"]] == ["120.00"]
    assert [(p["quantidade"], p["quantidade_pendente"]) for p in corpo["pecas"]] == [(2, 0)]


async def test_gerente_tambem_inclui_itens(cliente_http, gerente, os_em_diagnostico, servico):
    resposta = await _incluir_servico(cliente_http, gerente, os_em_diagnostico["id"], servico["id"])

    assert resposta.status_code == 201


async def test_conclui_o_orcamento_e_congela_os_valores(
    cliente_http, mecanico, os_em_diagnostico, servico, peca, conexao
):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)

    resposta = await _concluir(cliente_http, mecanico, os_em_diagnostico["id"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "AGUARDANDO_APROVACAO"
    assert corpo["orcamento"] == {
        "subtotal_servicos": "120.00",
        "subtotal_pecas": "71.80",
        "total": "191.80",
    }
    assert [(p["quantidade_reservada"], p["quantidade_pendente"]) for p in corpo["pecas"]] == [
        (0, 2)
    ]
    registro = await conexao.execute(
        text(
            "SELECT status_anterior, status_novo, origem, usuario_id FROM historico_status_os "
            "WHERE os_id = :id AND status_novo = 'AGUARDANDO_APROVACAO'"
        ),
        {"id": os_em_diagnostico["id"]},
    )
    assert registro.one()[:3] == ("EM_DIAGNOSTICO", "AGUARDANDO_APROVACAO", "USUARIO")


async def test_reajuste_do_catalogo_depois_da_conclusao_nao_altera_o_orcamento(
    cliente_http, gerente, mecanico, os_em_diagnostico, servico, peca
):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)
    await _concluir(cliente_http, mecanico, os_em_diagnostico["id"])

    reajuste_servico = await cliente_http.put(
        f"/servicos/{servico['id']}",
        json=SERVICO | {"valor_base": "999.00", "tempo_estimado_minutos": 600},
        headers=_cabecalho(gerente),
    )
    reajuste_peca = await cliente_http.put(
        f"/pecas/{peca['id']}",
        json=PECA | {"preco_unitario": "500.00", "prazo_reposicao_dias": 90},
        headers=_cabecalho(gerente),
    )
    detalhe = await _detalhe(cliente_http, mecanico, os_em_diagnostico["id"])

    assert (reajuste_servico.status_code, reajuste_peca.status_code) == (200, 200)
    assert detalhe["orcamento"]["total"] == "191.80"
    assert detalhe["servicos"][0]["preco_congelado"] == "120.00"
    assert detalhe["servicos"][0]["tempo_estimado_minutos"] == 45
    assert detalhe["pecas"][0]["preco_unitario_congelado"] == "35.90"
    assert detalhe["pecas"][0]["prazo_reposicao_dias"] == 3


async def test_conclusao_congela_o_preco_vigente_no_momento_da_conclusao(
    cliente_http, gerente, mecanico, os_em_diagnostico, servico, peca
):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)
    await cliente_http.put(
        f"/servicos/{servico['id']}",
        json=SERVICO | {"valor_base": "200.00"},
        headers=_cabecalho(gerente),
    )

    resposta = await _concluir(cliente_http, mecanico, os_em_diagnostico["id"])

    assert resposta.json()["orcamento"]["subtotal_servicos"] == "200.00"


async def test_servico_e_peca_excluidos_nao_entram_na_os(
    cliente_http, gerente, mecanico, os_em_diagnostico, servico, peca
):
    await cliente_http.delete(f"/servicos/{servico['id']}", headers=_cabecalho(gerente))
    await cliente_http.delete(f"/pecas/{peca['id']}", headers=_cabecalho(gerente))

    resposta_servico = await _incluir_servico(
        cliente_http, mecanico, os_em_diagnostico["id"], servico["id"]
    )
    resposta_peca = await _incluir_peca(cliente_http, mecanico, os_em_diagnostico["id"], peca["id"])

    for resposta in (resposta_servico, resposta_peca):
        assert resposta.status_code == 422
        assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"
    detalhe = await _detalhe(cliente_http, mecanico, os_em_diagnostico["id"])
    assert (detalhe["servicos"], detalhe["pecas"]) == ([], [])


async def test_item_excluido_depois_de_incluido_impede_a_conclusao(
    cliente_http, gerente, mecanico, os_em_diagnostico, servico, peca
):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)
    await cliente_http.delete(f"/servicos/{servico['id']}", headers=_cabecalho(gerente))

    resposta = await _concluir(cliente_http, mecanico, os_em_diagnostico["id"])

    assert resposta.status_code == 422
    detalhe = await _detalhe(cliente_http, mecanico, os_em_diagnostico["id"])
    assert (detalhe["status"], detalhe["orcamento"]) == ("EM_DIAGNOSTICO", None)


async def test_item_repetido_responde_422(cliente_http, mecanico, os_em_diagnostico, servico, peca):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)

    servico_repetido = await _incluir_servico(
        cliente_http, mecanico, os_em_diagnostico["id"], servico["id"]
    )
    peca_repetida = await _incluir_peca(cliente_http, mecanico, os_em_diagnostico["id"], peca["id"])

    assert (servico_repetido.status_code, peca_repetida.status_code) == (422, 422)


async def test_inclusao_fora_de_em_diagnostico_responde_422(
    cliente_http, mecanico, os_recebida, servico, peca
):
    servico_em_recebida = await _incluir_servico(
        cliente_http, mecanico, os_recebida["id"], servico["id"]
    )
    peca_em_recebida = await _incluir_peca(cliente_http, mecanico, os_recebida["id"], peca["id"])

    assert (servico_em_recebida.status_code, peca_em_recebida.status_code) == (422, 422)
    assert servico_em_recebida.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_depois_da_conclusao_nao_inclui_nem_remove_itens(
    cliente_http, mecanico, os_em_diagnostico, servico, peca
):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)
    await _concluir(cliente_http, mecanico, os_em_diagnostico["id"])
    id_da_os = os_em_diagnostico["id"]

    remover_servico = await cliente_http.delete(
        f"/ordens-servico/{id_da_os}/servicos/{servico['id']}", headers=_cabecalho(mecanico)
    )
    remover_peca = await cliente_http.delete(
        f"/ordens-servico/{id_da_os}/pecas/{peca['id']}", headers=_cabecalho(mecanico)
    )
    concluir_de_novo = await _concluir(cliente_http, mecanico, id_da_os)

    assert (remover_servico.status_code, remover_peca.status_code) == (422, 422)
    assert concluir_de_novo.status_code == 422
    assert len((await _detalhe(cliente_http, mecanico, id_da_os))["servicos"]) == 1


async def test_concluir_orcamento_de_os_recebida_responde_422(cliente_http, mecanico, os_recebida):
    resposta = await _concluir(cliente_http, mecanico, os_recebida["id"])

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_remove_servico_e_peca(cliente_http, mecanico, os_em_diagnostico, servico, peca):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)
    id_da_os = os_em_diagnostico["id"]

    remover_servico = await cliente_http.delete(
        f"/ordens-servico/{id_da_os}/servicos/{servico['id']}", headers=_cabecalho(mecanico)
    )
    remover_peca = await cliente_http.delete(
        f"/ordens-servico/{id_da_os}/pecas/{peca['id']}", headers=_cabecalho(mecanico)
    )

    assert (remover_servico.status_code, remover_peca.status_code) == (204, 204)
    detalhe = await _detalhe(cliente_http, mecanico, id_da_os)
    assert (detalhe["servicos"], detalhe["pecas"]) == ([], [])


@pytest.mark.parametrize(
    ("quantidade", "status", "codigo"),
    [
        (0, 400, "VALOR_INVALIDO"),
        (-1, 400, "VALOR_INVALIDO"),
        (1.5, 422, "ENTRADA_INVALIDA"),
        ("duas", 422, "ENTRADA_INVALIDA"),
        (MAIOR_INTEIRO + 1, 422, "ENTRADA_INVALIDA"),
    ],
)
async def test_quantidade_invalida_da_peca(
    cliente_http, mecanico, os_em_diagnostico, peca, quantidade, status, codigo
):
    resposta = await _incluir_peca(
        cliente_http, mecanico, os_em_diagnostico["id"], peca["id"], quantidade
    )

    assert resposta.status_code == status
    assert resposta.json()["codigo"] == codigo


async def test_ids_inexistentes_respondem_404(
    cliente_http, mecanico, os_em_diagnostico, servico, peca
):
    id_da_os = os_em_diagnostico["id"]

    respostas = [
        await _incluir_servico(cliente_http, mecanico, str(uuid4()), servico["id"]),
        await _incluir_servico(cliente_http, mecanico, id_da_os, str(uuid4())),
        await _incluir_peca(cliente_http, mecanico, str(uuid4()), peca["id"]),
        await _incluir_peca(cliente_http, mecanico, id_da_os, str(uuid4())),
        await cliente_http.delete(
            f"/ordens-servico/{id_da_os}/servicos/{uuid4()}", headers=_cabecalho(mecanico)
        ),
        await cliente_http.delete(
            f"/ordens-servico/{id_da_os}/pecas/{uuid4()}", headers=_cabecalho(mecanico)
        ),
        await _concluir(cliente_http, mecanico, str(uuid4())),
    ]

    assert [r.status_code for r in respostas] == [404] * 7


async def test_atendente_nao_altera_itens_nem_conclui(
    cliente_http, atendente, os_em_diagnostico, servico
):
    inclusao = await _incluir_servico(
        cliente_http, atendente, os_em_diagnostico["id"], servico["id"]
    )
    conclusao = await _concluir(cliente_http, atendente, os_em_diagnostico["id"])

    assert (inclusao.status_code, conclusao.status_code) == (403, 403)


async def test_sem_token_responde_401(cliente_http, os_em_diagnostico):
    resposta = await cliente_http.post(f"/ordens-servico/{os_em_diagnostico['id']}/orcamento")

    assert resposta.status_code == 401


class GravadorDeTeste(EventHandler):
    def __init__(self, sessao, tabela: str, falhar: bool):
        self._sessao = sessao
        self._tabela = tabela
        self._falhar = falhar

    async def tratar(self, evento):
        if self._falhar:
            raise RuntimeError("falha simulada na reserva")
        await self._sessao.execute(
            text(f"INSERT INTO {self._tabela} (evento_id) VALUES (:id)"), {"id": str(evento.os_id)}
        )
        return []


@pytest.fixture
async def tabela_do_handler(conexao):
    nome = f"teste_orcamento_{uuid4().hex}"
    await conexao.execute(text(f"CREATE TABLE {nome} (evento_id text PRIMARY KEY)"))
    return nome


async def test_o_evento_e_tratado_na_mesma_transacao_da_conclusao(
    cliente_http,
    mecanico,
    os_em_diagnostico,
    servico,
    peca,
    conexao,
    tabela_do_handler,
    monkeypatch,
):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            (
                OrcamentoFinalizadoEvent,
                lambda sessao: GravadorDeTeste(sessao, tabela_do_handler, False),
            )
        ],
    )

    resposta = await _concluir(cliente_http, mecanico, os_em_diagnostico["id"])

    assert resposta.status_code == 200
    gravados = await conexao.scalar(text(f"SELECT evento_id FROM {tabela_do_handler}"))
    assert gravados == os_em_diagnostico["id"]


async def test_falha_do_handler_desfaz_a_conclusao_inteira(
    cliente_http,
    mecanico,
    os_em_diagnostico,
    servico,
    peca,
    conexao,
    tabela_do_handler,
    monkeypatch,
):
    await _os_com_itens(cliente_http, mecanico, os_em_diagnostico, servico, peca)
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            (
                OrcamentoFinalizadoEvent,
                lambda sessao: GravadorDeTeste(sessao, tabela_do_handler, True),
            )
        ],
    )

    with pytest.raises(RuntimeError, match="falha simulada na reserva"):
        await _concluir(cliente_http, mecanico, os_em_diagnostico["id"])

    detalhe = await _detalhe(cliente_http, mecanico, os_em_diagnostico["id"])
    assert (detalhe["status"], detalhe["orcamento"]) == ("EM_DIAGNOSTICO", None)
    assert len(detalhe["historico"]) == 2
    assert await conexao.scalar(text(f"SELECT count(*) FROM {tabela_do_handler}")) == 0
