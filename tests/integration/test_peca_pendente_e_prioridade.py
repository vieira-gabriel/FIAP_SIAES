"""Peça pendente e prioridade entre duas OS pela data de abertura, pelas rotas HTTP e com
PostgreSQL real (RNF-13, RF-18, RF-19)."""

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


class Oficina:
    """Uma peça sem saldo e as OS que a disputam, sempre pelas rotas HTTP."""

    def __init__(self, cliente_http, atendente, mecanico, gerente):
        self.http = cliente_http
        self.atendente = atendente
        self.mecanico = mecanico
        self.gerente = gerente
        self.peca_id = ""

    async def cadastrar_peca(self) -> None:
        resposta = await self.http.post("/pecas", json=PECA, headers=_cabecalho(self.gerente))
        assert resposta.status_code == 201
        self.peca_id = resposta.json()["id"]

    async def abrir_os_com_orcamento(self, quantidade: int) -> dict:
        """Abre a OS, o mecânico a assume, inclui a peça e conclui o orçamento."""
        aberta = await self.http.post(
            "/ordens-servico", json=ABERTURA, headers=_cabecalho(self.atendente)
        )
        os = aberta.json()
        base = f"/ordens-servico/{os['id']}"
        await self.http.post(f"{base}/mecanico", headers=_cabecalho(self.mecanico))
        await self.http.post(
            f"{base}/pecas",
            json={"peca_id": self.peca_id, "quantidade": quantidade},
            headers=_cabecalho(self.mecanico),
        )
        resposta = await self.http.post(f"{base}/orcamento", headers=_cabecalho(self.mecanico))
        assert resposta.status_code == 200
        return os

    async def aprovar(self, os: dict) -> dict:
        resposta = await self.http.post(
            "/acompanhamento/aprovacao", json={"numero": os["numero"], "documento": DOCUMENTO}
        )
        assert resposta.status_code == 200
        return resposta.json()

    async def repor(self, quantidade: int) -> None:
        resposta = await self.http.post(
            f"/pecas/{self.peca_id}/reposicao",
            json={"quantidade": quantidade},
            headers=_cabecalho(self.mecanico),
        )
        assert resposta.status_code == 200

    async def situacao(self, os: dict) -> tuple[str, int, int]:
        detalhe = (
            await self.http.get(f"/ordens-servico/{os['id']}", headers=_cabecalho(self.gerente))
        ).json()
        (peca,) = detalhe["pecas"]
        return detalhe["status"], peca["quantidade_reservada"], peca["quantidade_pendente"]

    async def historico(self, os: dict) -> list[dict]:
        detalhe = (
            await self.http.get(f"/ordens-servico/{os['id']}", headers=_cabecalho(self.gerente))
        ).json()
        return detalhe["historico"]

    async def estoque(self) -> tuple[int, int, int]:
        corpo = (
            await self.http.get(f"/pecas/{self.peca_id}", headers=_cabecalho(self.gerente))
        ).json()
        return corpo["quantidade_fisica"], corpo["quantidade_reservada"], corpo["saldo_disponivel"]


@pytest.fixture
async def oficina(cliente_http, atendente, mecanico, gerente) -> Oficina:
    oficina = Oficina(cliente_http, atendente, mecanico, gerente)
    await oficina.cadastrar_peca()
    return oficina


async def test_reposicao_para_uma_so_libera_a_mais_antiga_e_a_seguinte_libera_a_outra(oficina):
    antiga = await oficina.abrir_os_com_orcamento(quantidade=2)
    recente = await oficina.abrir_os_com_orcamento(quantidade=2)
    assert antiga["data_abertura"] < recente["data_abertura"]

    # Sem saldo: as duas ficam com a peça pendente, e a aprovação as leva a AGUARDANDO_PECA.
    assert await oficina.situacao(antiga) == ("AGUARDANDO_APROVACAO", 0, 2)
    assert await oficina.situacao(recente) == ("AGUARDANDO_APROVACAO", 0, 2)
    assert (await oficina.aprovar(antiga))["pecas_pendentes"] == [
        {"nome": "Filtro de óleo", "quantidade": 2}
    ]
    await oficina.aprovar(recente)
    assert await oficina.situacao(antiga) == ("AGUARDANDO_PECA", 0, 2)
    assert await oficina.situacao(recente) == ("AGUARDANDO_PECA", 0, 2)
    assert await oficina.estoque() == (0, 0, 0)

    # Reposição só para uma: a OS mais antiga é liberada, e a outra continua esperando.
    await oficina.repor(2)
    assert await oficina.situacao(antiga) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await oficina.situacao(recente) == ("AGUARDANDO_PECA", 0, 2)
    assert await oficina.estoque() == (2, 2, 0)
    liberacao = (await oficina.historico(antiga))[-1]
    assert (liberacao["status_anterior"], liberacao["status_novo"]) == (
        "AGUARDANDO_PECA",
        "AGUARDANDO_EXECUCAO",
    )
    assert (liberacao["origem"], liberacao["usuario_id"]) == ("SISTEMA", None)
    assert (await oficina.historico(recente))[-1]["status_novo"] == "AGUARDANDO_PECA"

    # Nova reposição: a segunda OS é liberada.
    await oficina.repor(2)
    assert await oficina.situacao(antiga) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await oficina.situacao(recente) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await oficina.estoque() == (4, 4, 0)
    liberacao = (await oficina.historico(recente))[-1]
    assert (liberacao["status_novo"], liberacao["origem"], liberacao["usuario_id"]) == (
        "AGUARDANDO_EXECUCAO",
        "SISTEMA",
        None,
    )


async def test_a_prioridade_e_pela_abertura_e_nao_pela_ordem_de_aprovacao(oficina):
    antiga = await oficina.abrir_os_com_orcamento(quantidade=2)
    recente = await oficina.abrir_os_com_orcamento(quantidade=2)
    await oficina.aprovar(recente)
    await oficina.aprovar(antiga)

    await oficina.repor(2)

    assert await oficina.situacao(antiga) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await oficina.situacao(recente) == ("AGUARDANDO_PECA", 0, 2)


async def test_reposicao_menor_que_a_quantidade_da_mais_antiga_nao_a_libera(oficina):
    antiga = await oficina.abrir_os_com_orcamento(quantidade=2)
    recente = await oficina.abrir_os_com_orcamento(quantidade=2)
    await oficina.aprovar(antiga)
    await oficina.aprovar(recente)

    await oficina.repor(1)

    assert await oficina.situacao(antiga) == ("AGUARDANDO_PECA", 1, 1)
    assert await oficina.situacao(recente) == ("AGUARDANDO_PECA", 0, 2)
    assert await oficina.estoque() == (1, 1, 0)

    await oficina.repor(3)

    assert await oficina.situacao(antiga) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await oficina.situacao(recente) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await oficina.estoque() == (4, 4, 0)


async def test_os_ainda_aguardando_aprovacao_tambem_recebe_a_reserva_pela_ordem_de_abertura(
    oficina,
):
    antiga = await oficina.abrir_os_com_orcamento(quantidade=2)
    recente = await oficina.abrir_os_com_orcamento(quantidade=2)

    await oficina.repor(2)

    assert await oficina.situacao(antiga) == ("AGUARDANDO_APROVACAO", 2, 0)
    assert await oficina.situacao(recente) == ("AGUARDANDO_APROVACAO", 0, 2)
    resposta = await oficina.aprovar(antiga)
    assert resposta["status"] == "AGUARDANDO_EXECUCAO"
    assert (await oficina.aprovar(recente))["status"] == "AGUARDANDO_PECA"


async def test_a_prioridade_segue_a_data_de_abertura_gravada_e_nao_a_ordem_de_criacao(
    oficina, conexao
):
    criada_primeiro = await oficina.abrir_os_com_orcamento(quantidade=2)
    criada_depois = await oficina.abrir_os_com_orcamento(quantidade=2)
    # A OS criada depois passa a ser a mais antiga. O primeiro UPDATE grava a da criada primeiro,
    # para a ordem física das linhas não coincidir com a ordem das datas.
    await conexao.execute(
        text("UPDATE ordens_servico SET data_abertura = now() + interval '1 day' WHERE id = :id"),
        {"id": criada_primeiro["id"]},
    )
    await conexao.execute(
        text("UPDATE ordens_servico SET data_abertura = now() - interval '1 day' WHERE id = :id"),
        {"id": criada_depois["id"]},
    )
    await oficina.aprovar(criada_primeiro)
    await oficina.aprovar(criada_depois)

    await oficina.repor(2)

    assert await oficina.situacao(criada_depois) == ("AGUARDANDO_EXECUCAO", 2, 0)
    assert await oficina.situacao(criada_primeiro) == ("AGUARDANDO_PECA", 0, 2)
