"""Itens da OS, conclusão do orçamento, reserva, alocação, baixa e estorno das peças pelas rotas
HTTP, com PostgreSQL real (RF-17, RF-18, RF-19, RF-20, RF-23, RNF-08, RNF-11, RNF-13)."""

from uuid import UUID, uuid4

import pytest
from asyncpg.exceptions import DeadlockDetectedError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from application.events.event_dispatcher import EventHandler
from domain.entities.usuario import Usuario
from domain.events.execucao_iniciada_event import ExecucaoIniciadaEvent
from domain.events.orcamento_finalizado_event import OrcamentoFinalizadoEvent
from domain.events.saldo_peca_atualizado_event import SaldoPecaAtualizadoEvent
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_estoque_repository import PostgresEstoqueRepository
from infrastructure.repositories.postgres_ordem_servico_repository import (
    PostgresOrdemServicoRepository,
)
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


async def _peca_com_saldo(cliente_http, gerente, saldo: int) -> dict:
    resposta = await cliente_http.post(
        "/pecas", json=PECA | {"quantidade_fisica_inicial": saldo}, headers=_cabecalho(gerente)
    )
    assert resposta.status_code == 201
    return resposta.json()


async def _estoque(cliente_http, quem, peca_id: str) -> tuple[int, int, int]:
    corpo = (await cliente_http.get(f"/pecas/{peca_id}", headers=_cabecalho(quem))).json()
    return corpo["quantidade_fisica"], corpo["quantidade_reservada"], corpo["saldo_disponivel"]


async def _os_orcada(cliente_http, atendente, mecanico, peca_id: str, quantidade: int) -> str:
    """Abre a OS, o mecânico a assume, inclui a peça e conclui o orçamento."""
    aberta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    os_id = aberta.json()["id"]
    await cliente_http.post(f"/ordens-servico/{os_id}/mecanico", headers=_cabecalho(mecanico))
    await _incluir_peca(cliente_http, mecanico, os_id, peca_id, quantidade)
    resposta = await _concluir(cliente_http, mecanico, os_id)
    assert resposta.status_code == 200
    return os_id


async def _reservada_e_pendente(cliente_http, quem, os_id: str) -> tuple[int, int]:
    (peca,) = (await _detalhe(cliente_http, quem, os_id))["pecas"]
    return peca["quantidade_reservada"], peca["quantidade_pendente"]


async def test_conclusao_reserva_toda_a_quantidade_quando_ha_saldo(
    cliente_http, atendente, mecanico, gerente
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=10)

    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)

    assert await _reservada_e_pendente(cliente_http, mecanico, os_id) == (2, 0)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (10, 2, 8)


async def test_conclusao_reserva_o_que_ha_e_deixa_o_resto_pendente(
    cliente_http, atendente, mecanico, gerente
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=1)

    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)

    assert await _reservada_e_pendente(cliente_http, mecanico, os_id) == (1, 1)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (1, 1, 0)


async def test_conclusao_com_peca_sem_saldo_registra_o_pendente(
    cliente_http, atendente, mecanico, peca
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)

    detalhe = await _detalhe(cliente_http, mecanico, os_id)

    assert detalhe["status"] == "AGUARDANDO_APROVACAO"
    assert [(p["quantidade_reservada"], p["quantidade_pendente"]) for p in detalhe["pecas"]] == [
        (0, 2)
    ]
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (0, 0, 0)


async def test_saldo_que_sobra_vai_primeiro_para_a_os_aberta_antes(
    cliente_http, atendente, mecanico, gerente
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=3)
    primeira = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    segunda = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    assert await _reservada_e_pendente(cliente_http, mecanico, primeira) == (2, 0)
    assert await _reservada_e_pendente(cliente_http, mecanico, segunda) == (1, 1)
    await cliente_http.post(
        f"/pecas/{peca['id']}/reposicao", json={"quantidade": 1}, headers=_cabecalho(gerente)
    )

    terceira = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=1)

    assert await _reservada_e_pendente(cliente_http, mecanico, segunda) == (2, 0)
    assert await _reservada_e_pendente(cliente_http, mecanico, terceira) == (0, 1)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (4, 4, 0)


async def test_falha_de_um_handler_depois_da_reserva_desfaz_a_reserva(
    cliente_http, atendente, mecanico, gerente, conexao, tabela_do_handler, monkeypatch
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    aberta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    os_id = aberta.json()["id"]
    await cliente_http.post(f"/ordens-servico/{os_id}/mecanico", headers=_cabecalho(mecanico))
    await _incluir_peca(cliente_http, mecanico, os_id, peca["id"], 2)
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            *app.state.fabricas_de_handlers,
            (
                OrcamentoFinalizadoEvent,
                lambda sessao: GravadorDeTeste(sessao, tabela_do_handler, True),
            ),
        ],
    )

    with pytest.raises(RuntimeError, match="falha simulada na reserva"):
        await _concluir(cliente_http, mecanico, os_id)

    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 0, 5)
    detalhe = await _detalhe(cliente_http, mecanico, os_id)
    assert (detalhe["status"], detalhe["pecas"][0]["quantidade_pendente"]) == ("EM_DIAGNOSTICO", 0)


async def _aprovar(fabrica_de_sessoes, os_id: str) -> None:
    """A rota de aprovação do cliente é a issue #100; aqui a aprovação usa o domínio."""
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)
        os = await ordens.buscar_por_id(UUID(os_id))
        os.aprovar_orcamento()
        await ordens.salvar(os)


async def _repor(cliente_http, quem, peca_id: str, quantidade: int):
    return await cliente_http.post(
        f"/pecas/{peca_id}/reposicao", json={"quantidade": quantidade}, headers=_cabecalho(quem)
    )


async def _situacao(cliente_http, quem, os_id: str) -> tuple[str, int, int]:
    detalhe = await _detalhe(cliente_http, quem, os_id)
    (peca,) = detalhe["pecas"]
    return detalhe["status"], peca["quantidade_reservada"], peca["quantidade_pendente"]


async def test_reposicao_libera_a_os_em_aguardando_peca_para_a_execucao(
    cliente_http, atendente, mecanico, peca, fabrica_de_sessoes
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    await _aprovar(fabrica_de_sessoes, os_id)
    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_PECA", 0, 2)

    resposta = await _repor(cliente_http, mecanico, peca["id"], 2)

    assert resposta.status_code == 200
    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_EXECUCAO", 2, 0)
    registro = (await _detalhe(cliente_http, mecanico, os_id))["historico"][-1]
    assert (registro["status_anterior"], registro["status_novo"]) == (
        "AGUARDANDO_PECA",
        "AGUARDANDO_EXECUCAO",
    )
    assert (registro["origem"], registro["usuario_id"]) == ("SISTEMA", None)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (2, 2, 0)


async def test_reposicao_para_uma_so_das_duas_os_pendentes_atende_a_mais_antiga(
    cliente_http, atendente, mecanico, peca, fabrica_de_sessoes
):
    mais_antiga = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    mais_nova = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    await _aprovar(fabrica_de_sessoes, mais_antiga)
    await _aprovar(fabrica_de_sessoes, mais_nova)

    await _repor(cliente_http, mecanico, peca["id"], 2)

    assert await _situacao(cliente_http, mecanico, mais_antiga) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await _situacao(cliente_http, mecanico, mais_nova) == ("AGUARDANDO_PECA", 0, 2)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (2, 2, 0)


async def test_reposicao_maior_atende_a_mais_antiga_e_parte_da_seguinte(
    cliente_http, atendente, mecanico, peca, fabrica_de_sessoes
):
    mais_antiga = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    mais_nova = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    await _aprovar(fabrica_de_sessoes, mais_antiga)
    await _aprovar(fabrica_de_sessoes, mais_nova)

    await _repor(cliente_http, mecanico, peca["id"], 3)

    assert await _situacao(cliente_http, mecanico, mais_antiga) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await _situacao(cliente_http, mecanico, mais_nova) == ("AGUARDANDO_PECA", 1, 1)


async def test_reposicao_reserva_para_a_os_que_ainda_aguarda_a_aprovacao(
    cliente_http, atendente, mecanico, peca
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)

    await _repor(cliente_http, mecanico, peca["id"], 2)

    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_APROVACAO", 2, 0)


async def test_ajuste_da_quantidade_fisica_para_cima_tambem_aloca(
    cliente_http, atendente, mecanico, peca, fabrica_de_sessoes
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    await _aprovar(fabrica_de_sessoes, os_id)

    resposta = await cliente_http.put(
        f"/pecas/{peca['id']}/quantidade-fisica",
        json={"quantidade_fisica": 5},
        headers=_cabecalho(mecanico),
    )

    assert resposta.status_code == 200
    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)


async def test_reposicao_sem_os_pendente_so_soma_ao_estoque(cliente_http, mecanico, peca):
    resposta = await _repor(cliente_http, mecanico, peca["id"], 4)

    assert resposta.status_code == 200
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (4, 0, 4)


class FalhaDeTeste(EventHandler):
    async def tratar(self, evento):
        raise RuntimeError("falha simulada depois da alocação")


async def test_falha_de_um_handler_depois_da_alocacao_desfaz_a_reposicao(
    cliente_http, atendente, mecanico, peca, fabrica_de_sessoes, monkeypatch
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    await _aprovar(fabrica_de_sessoes, os_id)
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            *app.state.fabricas_de_handlers,
            (
                SaldoPecaAtualizadoEvent,
                lambda sessao: FalhaDeTeste(),
            ),
        ],
    )

    with pytest.raises(RuntimeError, match="falha simulada depois da alocação"):
        await _repor(cliente_http, mecanico, peca["id"], 2)

    assert await _estoque(cliente_http, mecanico, peca["id"]) == (0, 0, 0)
    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_PECA", 0, 2)


async def _cancelar(cliente_http, quem, os_id: str, motivo: str = "Cliente desistiu do serviço"):
    return await cliente_http.post(
        f"/ordens-servico/{os_id}/cancelamento", json={"motivo": motivo}, headers=_cabecalho(quem)
    )


async def test_cancelamento_devolve_as_reservas_ao_saldo_disponivel(
    cliente_http, atendente, mecanico, gerente
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)

    resposta = await _cancelar(cliente_http, gerente, os_id)

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 0, 5)
    registro = (await _detalhe(cliente_http, gerente, os_id))["historico"][-1]
    assert (registro["status_novo"], registro["motivo"], registro["origem"]) == (
        "CANCELADA",
        "Cliente desistiu do serviço",
        "USUARIO",
    )
    assert registro["usuario_id"] == str(gerente.id)


async def test_cancelamento_remove_a_pendencia_e_a_reposicao_nao_aloca_a_os_cancelada(
    cliente_http, atendente, mecanico, gerente, peca
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_APROVACAO", 0, 2)

    await _cancelar(cliente_http, gerente, os_id)
    await _repor(cliente_http, mecanico, peca["id"], 2)

    assert await _situacao(cliente_http, mecanico, os_id) == ("CANCELADA", 0, 0)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (2, 0, 2)


async def test_saldo_devolvido_pelo_cancelamento_libera_a_os_que_esperava_a_peca(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=2)
    dona = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    esperando = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    await _aprovar(fabrica_de_sessoes, esperando)
    assert await _situacao(cliente_http, mecanico, esperando) == ("AGUARDANDO_PECA", 0, 2)

    await _cancelar(cliente_http, gerente, dona)

    assert await _situacao(cliente_http, mecanico, esperando) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (2, 2, 0)


@pytest.mark.parametrize("motivo", ["", "   "])
async def test_cancelamento_sem_motivo_responde_422_e_mantem_as_reservas(
    cliente_http, atendente, mecanico, gerente, motivo
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)

    resposta = await _cancelar(cliente_http, gerente, os_id, motivo)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)


async def test_cancelamento_sem_o_campo_motivo_responde_422(
    cliente_http, atendente, mecanico, gerente, peca
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=1)

    resposta = await cliente_http.post(
        f"/ordens-servico/{os_id}/cancelamento", json={}, headers=_cabecalho(gerente)
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"


async def test_cancelamento_com_marcacao_no_motivo_responde_400_e_nada_muda(
    cliente_http, atendente, mecanico, gerente
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)

    resposta = await _cancelar(cliente_http, gerente, os_id, "<script>alert(1)</script>")

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"
    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_APROVACAO", 2, 0)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)


async def test_motivo_com_acentos_e_simbolos_comuns_e_gravado_como_digitado(
    cliente_http, atendente, mecanico, gerente, peca
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=1)
    motivo = "Cliente não aprovou: R$ 1.200 & prazo > 10 dias"

    resposta = await _cancelar(cliente_http, gerente, os_id, motivo)

    assert resposta.status_code == 200
    assert (await _detalhe(cliente_http, gerente, os_id))["historico"][-1]["motivo"] == motivo


async def _levar_a_entrega(fabrica_de_sessoes, os_id: str, mecanico: Usuario, entregar: bool):
    """As rotas de execução, conclusão e entrega são das issues #99 a #101; aqui o domínio."""
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)
        os = await ordens.buscar_por_id(UUID(os_id))
        os.aprovar_orcamento()
        os.iniciar_execucao(mecanico)
        os.concluir_manutencao(mecanico)
        if entregar:
            os.entregar_veiculo(mecanico.id)
        await ordens.salvar(os)


@pytest.mark.parametrize("entregar", [False, True], ids=["FINALIZADA", "ENTREGUE"])
async def test_cancelamento_de_os_finalizada_ou_entregue_responde_422(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes, entregar
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=1)
    await _levar_a_entrega(fabrica_de_sessoes, os_id, mecanico, entregar)

    resposta = await _cancelar(cliente_http, gerente, os_id)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_cancelar_duas_vezes_responde_422_na_segunda(
    cliente_http, atendente, mecanico, gerente, peca
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=1)

    primeira = await _cancelar(cliente_http, gerente, os_id)
    segunda = await _cancelar(cliente_http, gerente, os_id)

    assert (primeira.status_code, segunda.status_code) == (200, 422)


async def test_cancelamento_de_os_inexistente_responde_404(cliente_http, gerente):
    resposta = await _cancelar(cliente_http, gerente, str(uuid4()))

    assert resposta.status_code == 404


@pytest.mark.parametrize("quem", ["atendente", "mecanico"])
async def test_so_o_gerente_cancela(cliente_http, request, atendente, mecanico, gerente, quem):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=1)

    resposta = await _cancelar(cliente_http, request.getfixturevalue(quem), os_id)

    assert resposta.status_code == 403
    assert (await _situacao(cliente_http, gerente, os_id))[0] == "AGUARDANDO_APROVACAO"


async def test_falha_de_um_handler_depois_do_estorno_desfaz_o_cancelamento(
    cliente_http, atendente, mecanico, gerente, monkeypatch
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            *app.state.fabricas_de_handlers,
            (SaldoPecaAtualizadoEvent, lambda sessao: FalhaDeTeste()),
        ],
    )

    with pytest.raises(RuntimeError, match="falha simulada depois da alocação"):
        await _cancelar(cliente_http, gerente, os_id)

    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)
    assert await _situacao(cliente_http, mecanico, os_id) == ("AGUARDANDO_APROVACAO", 2, 0)


async def test_impasse_no_cancelamento_e_repetido_e_a_resposta_e_200(
    cliente_http, atendente, mecanico, gerente, monkeypatch
):
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=5)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    salvar_original = PostgresEstoqueRepository.salvar
    tentativas = []

    async def salvar_com_impasse_na_primeira_vez(self, estoque):
        tentativas.append(estoque.peca_id)
        if len(tentativas) == 1:
            raise DBAPIError("UPDATE estoque_pecas", None, DeadlockDetectedError())
        await salvar_original(self, estoque)

    monkeypatch.setattr(PostgresEstoqueRepository, "salvar", salvar_com_impasse_na_primeira_vez)

    resposta = await _cancelar(cliente_http, gerente, os_id)

    assert resposta.status_code == 200
    assert len(tentativas) == 2
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 0, 5)
    historico = (await _detalhe(cliente_http, gerente, os_id))["historico"]
    assert [r["status_novo"] for r in historico].count("CANCELADA") == 1


async def _iniciar(cliente_http, quem, os_id: str):
    return await cliente_http.post(f"/ordens-servico/{os_id}/execucao", headers=_cabecalho(quem))


async def _os_aguardando_execucao(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes, saldo: int = 5
) -> tuple[str, dict]:
    peca = await _peca_com_saldo(cliente_http, gerente, saldo=saldo)
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)
    await _aprovar(fabrica_de_sessoes, os_id)
    assert (await _detalhe(cliente_http, mecanico, os_id))["status"] == "AGUARDANDO_EXECUCAO"
    return os_id, peca


async def test_inicio_da_execucao_da_baixa_nas_pecas_e_grava_o_inicio(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)

    resposta = await _iniciar(cliente_http, mecanico, os_id)

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "EM_EXECUCAO"
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (3, 0, 3)
    detalhe = await _detalhe(cliente_http, mecanico, os_id)
    assert detalhe["data_inicio_execucao"] is not None
    registro = detalhe["historico"][-1]
    assert (registro["status_anterior"], registro["status_novo"], registro["origem"]) == (
        "AGUARDANDO_EXECUCAO",
        "EM_EXECUCAO",
        "USUARIO",
    )
    assert registro["usuario_id"] == str(mecanico.id)


async def test_gerente_inicia_a_execucao_de_qualquer_os(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )

    resposta = await _iniciar(cliente_http, gerente, os_id)

    assert resposta.status_code == 200
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (3, 0, 3)


async def test_outro_mecanico_recebe_403_e_o_estoque_fica_intacto(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes, conexao
):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )
    outro = await _inserir_usuario(conexao, PerfilUsuario.MECANICO)

    resposta = await _iniciar(cliente_http, outro, os_id)

    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "SEM_PERMISSAO")
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)
    assert (await _detalhe(cliente_http, mecanico, os_id))["status"] == "AGUARDANDO_EXECUCAO"


async def test_inicio_fora_de_aguardando_execucao_responde_422(
    cliente_http, atendente, mecanico, gerente, peca
):
    os_id = await _os_orcada(cliente_http, atendente, mecanico, peca["id"], quantidade=2)

    resposta = await _iniciar(cliente_http, mecanico, os_id)

    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "REGRA_DE_NEGOCIO_VIOLADA")


async def test_iniciar_duas_vezes_responde_422_e_baixa_uma_vez_so(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )

    primeira = await _iniciar(cliente_http, mecanico, os_id)
    segunda = await _iniciar(cliente_http, mecanico, os_id)

    assert (primeira.status_code, segunda.status_code) == (200, 422)
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (3, 0, 3)


async def test_inicio_de_os_inexistente_responde_404(cliente_http, mecanico):
    resposta = await _iniciar(cliente_http, mecanico, str(uuid4()))

    assert resposta.status_code == 404


async def test_cancelamento_depois_do_inicio_nao_devolve_as_pecas_baixadas(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )
    await _iniciar(cliente_http, mecanico, os_id)

    resposta = await _cancelar(cliente_http, gerente, os_id)

    assert resposta.status_code == 200
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (3, 0, 3)


async def test_falha_de_um_handler_depois_da_baixa_desfaz_o_inicio(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes, monkeypatch
):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )
    monkeypatch.setattr(
        app.state,
        "fabricas_de_handlers",
        [
            *app.state.fabricas_de_handlers,
            (ExecucaoIniciadaEvent, lambda sessao: FalhaDeTeste()),
        ],
    )

    with pytest.raises(RuntimeError, match="falha simulada depois da alocação"):
        await _iniciar(cliente_http, mecanico, os_id)

    assert await _estoque(cliente_http, mecanico, peca["id"]) == (5, 2, 3)
    assert (await _detalhe(cliente_http, mecanico, os_id))["status"] == "AGUARDANDO_EXECUCAO"


async def test_impasse_no_inicio_da_execucao_e_repetido_e_a_resposta_e_200(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes, monkeypatch
):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )
    salvar_original = PostgresEstoqueRepository.salvar
    tentativas = []

    async def salvar_com_impasse_na_primeira_vez(self, estoque):
        tentativas.append(estoque.peca_id)
        if len(tentativas) == 1:
            raise DBAPIError("UPDATE estoque_pecas", None, DeadlockDetectedError())
        await salvar_original(self, estoque)

    monkeypatch.setattr(PostgresEstoqueRepository, "salvar", salvar_com_impasse_na_primeira_vez)

    resposta = await _iniciar(cliente_http, mecanico, os_id)

    assert resposta.status_code == 200
    assert len(tentativas) == 2
    assert await _estoque(cliente_http, mecanico, peca["id"]) == (3, 0, 3)


async def _concluir_manutencao(cliente_http, quem, os_id: str):
    return await cliente_http.post(f"/ordens-servico/{os_id}/conclusao", headers=_cabecalho(quem))


async def _os_em_execucao(cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes):
    os_id, peca = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )
    assert (await _iniciar(cliente_http, mecanico, os_id)).status_code == 200
    return os_id, peca


async def test_conclusao_finaliza_a_os_e_grava_o_momento_e_o_historico(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, _ = await _os_em_execucao(cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes)

    resposta = await _concluir_manutencao(cliente_http, mecanico, os_id)

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "FINALIZADA"
    detalhe = await _detalhe(cliente_http, mecanico, os_id)
    assert detalhe["data_finalizacao"] is not None
    registro = detalhe["historico"][-1]
    assert (registro["status_anterior"], registro["status_novo"], registro["origem"]) == (
        "EM_EXECUCAO",
        "FINALIZADA",
        "USUARIO",
    )
    assert registro["usuario_id"] == str(mecanico.id)


async def test_gerente_conclui_a_manutencao_de_qualquer_os(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, _ = await _os_em_execucao(cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes)

    resposta = await _concluir_manutencao(cliente_http, gerente, os_id)

    assert resposta.status_code == 200


async def test_outro_mecanico_nao_conclui(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes, conexao
):
    os_id, _ = await _os_em_execucao(cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes)
    outro = await _inserir_usuario(conexao, PerfilUsuario.MECANICO)

    resposta = await _concluir_manutencao(cliente_http, outro, os_id)

    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "SEM_PERMISSAO")
    assert (await _detalhe(cliente_http, mecanico, os_id))["status"] == "EM_EXECUCAO"


async def test_conclusao_fora_de_em_execucao_responde_422(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, _ = await _os_aguardando_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )

    resposta = await _concluir_manutencao(cliente_http, mecanico, os_id)

    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "REGRA_DE_NEGOCIO_VIOLADA")


async def test_concluir_duas_vezes_responde_422_na_segunda(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
):
    os_id, _ = await _os_em_execucao(cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes)

    primeira = await _concluir_manutencao(cliente_http, mecanico, os_id)
    segunda = await _concluir_manutencao(cliente_http, mecanico, os_id)

    assert (primeira.status_code, segunda.status_code) == (200, 422)


async def test_conclusao_de_os_inexistente_responde_404(cliente_http, mecanico):
    assert (await _concluir_manutencao(cliente_http, mecanico, str(uuid4()))).status_code == 404


async def test_itens_ficam_bloqueados_depois_da_finalizacao(
    cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes, servico
):
    os_id, peca_da_os = await _os_em_execucao(
        cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes
    )
    outra_peca = await cliente_http.post(
        "/pecas",
        json=PECA | {"codigo_referencia": "VLA-002", "nome": "Vela"},
        headers=_cabecalho(gerente),
    )
    await _concluir_manutencao(cliente_http, mecanico, os_id)

    inclusao_servico = await _incluir_servico(cliente_http, mecanico, os_id, servico["id"])
    inclusao_peca = await _incluir_peca(cliente_http, mecanico, os_id, outra_peca.json()["id"])
    remocao_peca = await cliente_http.delete(
        f"/ordens-servico/{os_id}/pecas/{peca_da_os['id']}", headers=_cabecalho(mecanico)
    )

    for resposta in (inclusao_servico, inclusao_peca, remocao_peca):
        assert resposta.status_code == 422
        assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"
    detalhe = await _detalhe(cliente_http, mecanico, os_id)
    assert (len(detalhe["servicos"]), len(detalhe["pecas"])) == (0, 1)
