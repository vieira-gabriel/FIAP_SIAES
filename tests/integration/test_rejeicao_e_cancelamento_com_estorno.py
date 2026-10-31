"""Os dois caminhos que levam a `CANCELADA`, com o estorno das reservas, pelas rotas HTTP e com
PostgreSQL real (RNF-13, RF-18, RF-23, RF-26)."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

DOCUMENTO = "529.982.247-25"
MOTIVO = "Cliente desistiu do serviço"
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


class Oficina:
    """Uma peça com saldo e a OS que a reserva, sempre pelas rotas HTTP."""

    def __init__(self, cliente_http, atendente, mecanico, gerente):
        self.http = cliente_http
        self.atendente = atendente
        self.mecanico = mecanico
        self.gerente = gerente
        self.peca_id = ""
        self.os: dict = {}

    async def preparar(self, saldo: int = 5, quantidade: int = 2) -> None:
        """Cadastra a peça e leva a OS até a conclusão do orçamento, com a peça reservada."""
        peca = await self.http.post(
            "/pecas",
            json=PECA | {"quantidade_fisica_inicial": saldo},
            headers=_cabecalho(self.gerente),
        )
        self.peca_id = peca.json()["id"]
        aberta = await self.http.post(
            "/ordens-servico", json=ABERTURA, headers=_cabecalho(self.atendente)
        )
        self.os = aberta.json()
        base = f"/ordens-servico/{self.os['id']}"
        await self.http.post(f"{base}/mecanico", headers=_cabecalho(self.mecanico))
        await self.http.post(
            f"{base}/pecas",
            json={"peca_id": self.peca_id, "quantidade": quantidade},
            headers=_cabecalho(self.mecanico),
        )
        resposta = await self.http.post(f"{base}/orcamento", headers=_cabecalho(self.mecanico))
        assert resposta.status_code == 200

    async def aprovar(self) -> None:
        resposta = await self.http.post(
            "/acompanhamento/aprovacao",
            json={"numero": self.os["numero"], "documento": DOCUMENTO},
        )
        assert resposta.status_code == 200

    async def iniciar_execucao(self) -> None:
        resposta = await self.http.post(
            f"/ordens-servico/{self.os['id']}/execucao", headers=_cabecalho(self.mecanico)
        )
        assert resposta.status_code == 200

    async def rejeitar(self):
        return await self.http.post(
            "/acompanhamento/rejeicao",
            json={"numero": self.os["numero"], "documento": DOCUMENTO},
        )

    async def cancelar(self, motivo: str = MOTIVO):
        return await self.http.post(
            f"/ordens-servico/{self.os['id']}/cancelamento",
            json={"motivo": motivo},
            headers=_cabecalho(self.gerente),
        )

    async def detalhe(self) -> dict:
        resposta = await self.http.get(
            f"/ordens-servico/{self.os['id']}", headers=_cabecalho(self.gerente)
        )
        return resposta.json()

    async def estoque(self) -> tuple[int, int, int]:
        corpo = (
            await self.http.get(f"/pecas/{self.peca_id}", headers=_cabecalho(self.gerente))
        ).json()
        return corpo["quantidade_fisica"], corpo["quantidade_reservada"], corpo["saldo_disponivel"]

    async def ultimo_registro(self) -> dict:
        return (await self.detalhe())["historico"][-1]


@pytest.fixture
async def oficina(cliente_http, atendente, mecanico, gerente) -> Oficina:
    oficina = Oficina(cliente_http, atendente, mecanico, gerente)
    await oficina.preparar()
    return oficina


async def test_rejeicao_pelo_cliente_em_aguardando_aprovacao_devolve_as_reservas(oficina):
    assert (await oficina.detalhe())["status"] == "AGUARDANDO_APROVACAO"
    assert await oficina.estoque() == (5, 2, 3)

    resposta = await oficina.rejeitar()

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"
    assert await oficina.estoque() == (5, 0, 5)
    registro = await oficina.ultimo_registro()
    assert (registro["status_anterior"], registro["status_novo"]) == (
        "AGUARDANDO_APROVACAO",
        "CANCELADA",
    )
    assert (registro["origem"], registro["usuario_id"], registro["motivo"]) == (
        "CLIENTE",
        None,
        None,
    )


async def test_cancelamento_pelo_gerente_em_aguardando_execucao_devolve_as_reservas(oficina):
    await oficina.aprovar()
    assert (await oficina.detalhe())["status"] == "AGUARDANDO_EXECUCAO"
    assert await oficina.estoque() == (5, 2, 3)

    resposta = await oficina.cancelar()

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"
    assert await oficina.estoque() == (5, 0, 5)
    registro = await oficina.ultimo_registro()
    assert (registro["status_anterior"], registro["status_novo"]) == (
        "AGUARDANDO_EXECUCAO",
        "CANCELADA",
    )
    assert (registro["origem"], registro["usuario_id"], registro["motivo"]) == (
        "USUARIO",
        str(oficina.gerente.id),
        MOTIVO,
    )


async def test_cancelamento_pelo_gerente_em_execucao_considera_as_pecas_baixadas_consumidas(
    oficina,
):
    await oficina.aprovar()
    await oficina.iniciar_execucao()
    assert await oficina.estoque() == (3, 0, 3)

    resposta = await oficina.cancelar()

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"
    assert await oficina.estoque() == (3, 0, 3)
    registro = await oficina.ultimo_registro()
    assert (registro["status_anterior"], registro["status_novo"]) == ("EM_EXECUCAO", "CANCELADA")
    assert registro["motivo"] == MOTIVO


async def test_saldo_devolvido_pela_rejeicao_libera_a_os_que_esperava_a_peca(
    cliente_http, atendente, mecanico, gerente
):
    # Duas OS disputam 5 unidades: a primeira reserva 3, e a segunda, 2, com 1 pendente.
    primeira = Oficina(cliente_http, atendente, mecanico, gerente)
    await primeira.preparar(saldo=5, quantidade=3)
    segunda = Oficina(cliente_http, atendente, mecanico, gerente)
    segunda.peca_id = primeira.peca_id
    aberta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    segunda.os = aberta.json()
    base = f"/ordens-servico/{segunda.os['id']}"
    await cliente_http.post(f"{base}/mecanico", headers=_cabecalho(mecanico))
    await cliente_http.post(
        f"{base}/pecas",
        json={"peca_id": primeira.peca_id, "quantidade": 3},
        headers=_cabecalho(mecanico),
    )
    await cliente_http.post(f"{base}/orcamento", headers=_cabecalho(mecanico))
    await segunda.aprovar()
    assert (await segunda.detalhe())["status"] == "AGUARDANDO_PECA"
    assert await primeira.estoque() == (5, 5, 0)

    await primeira.rejeitar()

    assert (await segunda.detalhe())["status"] == "AGUARDANDO_EXECUCAO"
    assert await primeira.estoque() == (5, 3, 2)
