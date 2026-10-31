"""Fluxo completo da OS, da abertura à entrega, só pelas rotas HTTP e com PostgreSQL real
(RNF-13, RF-13 a RF-22, RF-24, RF-26)."""

from datetime import datetime
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
    "quantidade_fisica_inicial": 5,
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


class Fluxo:
    """Uma OS percorrendo as rotas, com as consultas de status, histórico e estoque."""

    def __init__(self, cliente_http, atendente, mecanico, gerente):
        self.http = cliente_http
        self.atendente = atendente
        self.mecanico = mecanico
        self.gerente = gerente
        self.os_id = ""
        self.numero = ""
        self.peca_id = ""

    async def chamar(self, metodo: str, caminho: str, quem: Usuario | None = None, **kwargs):
        cabecalho = _cabecalho(quem) if quem else {}
        return await self.http.request(metodo, caminho, headers=cabecalho, **kwargs)

    async def post_ok(self, caminho: str, quem: Usuario | None = None, **kwargs) -> dict:
        resposta = await self.chamar("POST", caminho, quem, **kwargs)
        assert resposta.status_code in (200, 201), (caminho, resposta.status_code, resposta.text)
        return resposta.json()

    async def detalhe(self) -> dict:
        resposta = await self.chamar("GET", f"/ordens-servico/{self.os_id}", self.gerente)
        return resposta.json()

    async def estoque(self) -> tuple[int, int, int]:
        corpo = (await self.chamar("GET", f"/pecas/{self.peca_id}", self.gerente)).json()
        return corpo["quantidade_fisica"], corpo["quantidade_reservada"], corpo["saldo_disponivel"]

    async def conferir(self, status: str, estoque: tuple[int, int, int], transicoes: int) -> dict:
        detalhe = await self.detalhe()
        assert detalhe["status"] == status
        assert await self.estoque() == estoque
        assert len(detalhe["historico"]) == transicoes
        assert detalhe["historico"][-1]["status_novo"] == status
        return detalhe


async def test_da_abertura_a_entrega_o_status_o_historico_e_o_estoque_a_cada_etapa(
    cliente_http, atendente, mecanico, gerente
):
    fluxo = Fluxo(cliente_http, atendente, mecanico, gerente)
    servico = await fluxo.post_ok("/servicos", gerente, json=SERVICO)
    peca = await fluxo.post_ok("/pecas", gerente, json=PECA)
    fluxo.peca_id = peca["id"]
    assert await fluxo.estoque() == (5, 0, 5)

    # RF-13: abertura pelo atendente.
    aberta = await fluxo.post_ok("/ordens-servico", atendente, json=ABERTURA)
    fluxo.os_id, fluxo.numero = aberta["id"], aberta["numero"]
    await fluxo.conferir("RECEBIDA", (5, 0, 5), transicoes=1)

    # RF-16: o mecânico assume a OS.
    await fluxo.post_ok(f"/ordens-servico/{fluxo.os_id}/mecanico", mecanico)
    await fluxo.conferir("EM_DIAGNOSTICO", (5, 0, 5), transicoes=2)

    # RF-17: itens incluídos; nada é reservado antes da conclusão do orçamento.
    base = f"/ordens-servico/{fluxo.os_id}"
    await fluxo.post_ok(f"{base}/servicos", mecanico, json={"servico_id": servico["id"]})
    itens = await fluxo.post_ok(
        f"{base}/pecas", mecanico, json={"peca_id": peca["id"], "quantidade": 2}
    )
    assert itens["orcamento"] is None
    detalhe = await fluxo.conferir("EM_DIAGNOSTICO", (5, 0, 5), transicoes=2)
    assert detalhe["orcamento"] is None

    # RF-17 e RF-18: orçamento concluído, valores congelados e peças reservadas.
    orcado = await fluxo.post_ok(f"{base}/orcamento", mecanico)
    assert orcado["orcamento"] == {
        "subtotal_servicos": "120.00",
        "subtotal_pecas": "71.80",
        "total": "191.80",
    }
    detalhe = await fluxo.conferir("AGUARDANDO_APROVACAO", (5, 2, 3), transicoes=3)
    assert [(p["quantidade_reservada"], p["quantidade_pendente"]) for p in detalhe["pecas"]] == [
        (2, 0)
    ]

    # RF-25: o cliente consulta a OS, sem token.
    consulta = await fluxo.post_ok(
        "/acompanhamento", json={"numero": fluxo.numero, "documento": DOCUMENTO}
    )
    assert (consulta["status"], consulta["valor_total"], consulta["pecas_pendentes"]) == (
        "AGUARDANDO_APROVACAO",
        "191.80",
        [],
    )

    # RF-26: o cliente aprova, e a OS aguarda a execução, com as reservas mantidas.
    aprovada = await fluxo.post_ok(
        "/acompanhamento/aprovacao", json={"numero": fluxo.numero, "documento": DOCUMENTO}
    )
    assert aprovada["status"] == "AGUARDANDO_EXECUCAO"
    await fluxo.conferir("AGUARDANDO_EXECUCAO", (5, 2, 3), transicoes=4)

    # RF-20: o início da execução dá baixa nas peças reservadas.
    await fluxo.post_ok(f"{base}/execucao", mecanico)
    detalhe = await fluxo.conferir("EM_EXECUCAO", (3, 0, 3), transicoes=5)
    assert detalhe["data_inicio_execucao"] is not None
    assert detalhe["data_finalizacao"] is None

    # RF-21: conclusão da manutenção; os itens ficam bloqueados.
    await fluxo.post_ok(f"{base}/conclusao", mecanico)
    detalhe = await fluxo.conferir("FINALIZADA", (3, 0, 3), transicoes=6)
    assert detalhe["data_finalizacao"] is not None
    bloqueio = await fluxo.chamar(
        "POST", f"{base}/servicos", mecanico, json={"servico_id": servico["id"]}
    )
    assert bloqueio.status_code == 422

    # RF-22: o atendente entrega o veículo.
    await fluxo.post_ok(f"{base}/entrega", atendente)
    detalhe = await fluxo.conferir("ENTREGUE", (3, 0, 3), transicoes=7)

    # RF-24: um registro por transição, com a origem e o usuário corretos.
    etapas = [
        (r["status_anterior"], r["status_novo"], r["origem"], r["usuario_id"])
        for r in detalhe["historico"]
    ]
    assert etapas == [
        (None, "RECEBIDA", "USUARIO", str(atendente.id)),
        ("RECEBIDA", "EM_DIAGNOSTICO", "USUARIO", str(mecanico.id)),
        ("EM_DIAGNOSTICO", "AGUARDANDO_APROVACAO", "USUARIO", str(mecanico.id)),
        ("AGUARDANDO_APROVACAO", "AGUARDANDO_EXECUCAO", "CLIENTE", None),
        ("AGUARDANDO_EXECUCAO", "EM_EXECUCAO", "USUARIO", str(mecanico.id)),
        ("EM_EXECUCAO", "FINALIZADA", "USUARIO", str(mecanico.id)),
        ("FINALIZADA", "ENTREGUE", "USUARIO", str(atendente.id)),
    ]
    momentos = [datetime.fromisoformat(r["data_hora"]) for r in detalhe["historico"]]
    assert momentos == sorted(momentos)
    assert detalhe["data_abertura"] <= detalhe["data_inicio_execucao"]
    assert detalhe["data_inicio_execucao"] <= detalhe["data_finalizacao"]

    # RF-25: depois da entrega, a consulta pública mostra o estado final.
    final = await fluxo.post_ok(
        "/acompanhamento", json={"numero": fluxo.numero, "documento": DOCUMENTO}
    )
    assert final["status"] == "ENTREGUE"
