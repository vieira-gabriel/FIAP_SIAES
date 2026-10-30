"""Abertura da OS pela rota HTTP, com PostgreSQL real (RF-13, RF-07, RF-04, RF-24, RNF-13)."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

CLIENTE = {"nome": "Maria Silva", "email": "maria@exemplo.com", "telefone": "11987654321"}
VEICULO = {"marca": "Fiat", "modelo": "Uno", "ano": 2015}
ABERTURA = {
    "documento": "529.982.247-25",
    "placa": "abc-1d23",
    "cliente": CLIENTE,
    "veiculo": VEICULO,
}


async def _cabecalho(conexao, perfil: PerfilUsuario) -> dict[str, str]:
    """Usuário gravado no banco: a OS guarda o atendente com chave estrangeira (RF-13)."""
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
    return {"Authorization": f"Bearer {app.state.token_service.emitir(usuario)}"}


@pytest.fixture
async def atendente(conexao):
    return await _cabecalho(conexao, PerfilUsuario.ATENDENTE)


@pytest.fixture
async def mecanico(conexao):
    return await _cabecalho(conexao, PerfilUsuario.MECANICO)


async def _abrir(cliente_http, cabecalho, dados=ABERTURA):
    return await cliente_http.post("/ordens-servico", json=dados, headers=cabecalho)


async def test_atendente_abre_os_com_cliente_e_veiculo_novos(cliente_http, atendente, conexao):
    resposta = await _abrir(cliente_http, atendente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "RECEBIDA"
    assert corpo["numero"].startswith("529-")
    assert corpo["mecanico_id"] is None

    gravada = await conexao.execute(
        text("SELECT status, numero FROM ordens_servico WHERE numero = :numero"),
        {"numero": corpo["numero"]},
    )
    assert gravada.one() == ("RECEBIDA", corpo["numero"])
    historico = await conexao.scalar(
        text("SELECT count(*) FROM historico_status_os WHERE os_id = :id"), {"id": corpo["id"]}
    )
    assert historico == 1


async def test_reabre_os_para_cliente_e_veiculo_ja_cadastrados(cliente_http, atendente):
    await _abrir(cliente_http, atendente)

    resposta = await _abrir(
        cliente_http, atendente, {"documento": "529.982.247-25", "placa": "ABC1D23"}
    )

    assert resposta.status_code == 201


async def test_gerente_tambem_abre_os(cliente_http, conexao):
    resposta = await _abrir(cliente_http, await _cabecalho(conexao, PerfilUsuario.GERENTE))

    assert resposta.status_code == 201


async def test_cliente_inexistente_sem_dados_responde_404(cliente_http, atendente):
    resposta = await _abrir(
        cliente_http, atendente, {"documento": "111.444.777-35", "placa": "ABC1D23"}
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


async def test_placa_de_veiculo_de_outro_cliente_responde_422(cliente_http, atendente):
    await _abrir(cliente_http, atendente)
    outro = {
        "documento": "111.444.777-35",
        "placa": "ABC1D23",
        "cliente": CLIENTE,
        "veiculo": VEICULO,
    }

    resposta = await _abrir(cliente_http, atendente, outro)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_placa_invalida_responde_400(cliente_http, atendente):
    resposta = await _abrir(cliente_http, atendente, ABERTURA | {"placa": "XX-123"})

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_mecanico_nao_abre_os(cliente_http, mecanico):
    resposta = await _abrir(cliente_http, mecanico)

    assert resposta.status_code == 403


async def test_sem_token_responde_401(cliente_http):
    resposta = await cliente_http.post("/ordens-servico", json=ABERTURA)

    assert resposta.status_code == 401


async def test_falha_na_gravacao_nao_deixa_cliente_nem_veiculo_para_tras(
    cliente_http, atendente, conexao, monkeypatch
):
    from infrastructure.repositories import postgres_ordem_servico_repository as adaptador

    async def falhar(self, os):
        raise RuntimeError("falha simulada ao gravar a OS")

    monkeypatch.setattr(adaptador.PostgresOrdemServicoRepository, "salvar", falhar)

    with pytest.raises(RuntimeError):
        await _abrir(
            cliente_http, atendente, ABERTURA | {"documento": "111.444.777-35", "placa": "DEF2G34"}
        )

    assert (
        await conexao.scalar(text("SELECT count(*) FROM clientes WHERE documento = '11144477735'"))
        == 0
    )
    assert await conexao.scalar(text("SELECT count(*) FROM veiculos WHERE placa = 'DEF2G34'")) == 0
