"""Atribuição do mecânico pela rota HTTP, com PostgreSQL real (RF-16, RF-24, RNF-13)."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from presentation.main import app

ABERTURA = {
    "documento": "529.982.247-25",
    "placa": "ABC1D23",
    "cliente": {"nome": "Maria Silva", "email": "maria@exemplo.com", "telefone": "11987654321"},
    "veiculo": {"marca": "Fiat", "modelo": "Uno", "ano": 2015},
}


async def _inserir_usuario(conexao, perfil: PerfilUsuario, ativo: bool = True) -> Usuario:
    """Usuário gravado no banco: a OS e o histórico guardam usuários com chave estrangeira."""
    usuario = Usuario(
        nome=perfil.value.title(),
        email=f"{perfil.value.lower()}-{uuid4().hex[:8]}@oficina.com",
        senha_hash="hash",
        perfil=perfil,
        ativo=ativo,
    )
    await conexao.execute(
        text(
            "INSERT INTO usuarios (id, nome, email, senha_hash, perfil, ativo) "
            "VALUES (:id, :nome, :email, :senha_hash, :perfil, :ativo)"
        ),
        {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "senha_hash": usuario.senha_hash,
            "perfil": perfil.value,
            "ativo": ativo,
        },
    )
    return usuario


def _cabecalho(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.state.token_service.emitir(usuario)}"}


@pytest.fixture
async def atendente(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.ATENDENTE)


@pytest.fixture
async def gerente(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.GERENTE)


@pytest.fixture
async def mecanico(conexao):
    return await _inserir_usuario(conexao, PerfilUsuario.MECANICO)


@pytest.fixture
async def os_recebida(cliente_http, atendente) -> dict:
    resposta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    assert resposta.status_code == 201
    return resposta.json()


async def _atribuir(cliente_http, quem: Usuario, os_id: str, corpo: dict | None = None):
    return await cliente_http.post(
        f"/ordens-servico/{os_id}/mecanico", json=corpo, headers=_cabecalho(quem)
    )


async def _ultimo_registro(conexao, os_id: str):
    linhas = await conexao.execute(
        text(
            "SELECT status_anterior, status_novo, origem, usuario_id FROM historico_status_os "
            "WHERE os_id = :id ORDER BY data_hora DESC, status_novo LIMIT 1"
        ),
        {"id": os_id},
    )
    return linhas.one()


async def test_mecanico_assume_a_os_sem_informar_o_mecanico(
    cliente_http, mecanico, os_recebida, conexao
):
    resposta = await _atribuir(cliente_http, mecanico, os_recebida["id"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "EM_DIAGNOSTICO"
    assert corpo["mecanico_id"] == str(mecanico.id)
    registro = await _ultimo_registro(conexao, os_recebida["id"])
    assert tuple(registro) == ("RECEBIDA", "EM_DIAGNOSTICO", "USUARIO", mecanico.id)


async def test_mecanico_pode_informar_o_proprio_id(cliente_http, mecanico, os_recebida):
    resposta = await _atribuir(
        cliente_http, mecanico, os_recebida["id"], {"mecanico_id": str(mecanico.id)}
    )

    assert resposta.status_code == 200
    assert resposta.json()["mecanico_id"] == str(mecanico.id)


async def test_gerente_atribui_a_os_e_o_historico_grava_o_gerente(
    cliente_http, gerente, mecanico, os_recebida, conexao
):
    resposta = await _atribuir(
        cliente_http, gerente, os_recebida["id"], {"mecanico_id": str(mecanico.id)}
    )

    assert resposta.status_code == 200
    assert resposta.json()["mecanico_id"] == str(mecanico.id)
    registro = await _ultimo_registro(conexao, os_recebida["id"])
    assert tuple(registro) == ("RECEBIDA", "EM_DIAGNOSTICO", "USUARIO", gerente.id)


async def test_detalhamento_mostra_o_mecanico_e_a_transicao(
    cliente_http, gerente, mecanico, os_recebida
):
    await _atribuir(cliente_http, gerente, os_recebida["id"], {"mecanico_id": str(mecanico.id)})

    detalhe = (
        await cliente_http.get(f"/ordens-servico/{os_recebida['id']}", headers=_cabecalho(gerente))
    ).json()

    assert (detalhe["status"], detalhe["mecanico_id"]) == ("EM_DIAGNOSTICO", str(mecanico.id))
    assert [r["status_novo"] for r in detalhe["historico"]] == ["RECEBIDA", "EM_DIAGNOSTICO"]
    assert detalhe["historico"][-1]["usuario_id"] == str(gerente.id)


@pytest.mark.parametrize("corpo", [None, {}, {"mecanico_id": None}])
async def test_gerente_sem_informar_o_mecanico_responde_400(
    cliente_http, gerente, os_recebida, corpo
):
    resposta = await _atribuir(cliente_http, gerente, os_recebida["id"], corpo)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "VALOR_INVALIDO"


async def test_mecanico_nao_atribui_a_os_a_outro_mecanico(
    cliente_http, conexao, mecanico, os_recebida
):
    outro = await _inserir_usuario(conexao, PerfilUsuario.MECANICO)

    resposta = await _atribuir(
        cliente_http, mecanico, os_recebida["id"], {"mecanico_id": str(outro.id)}
    )

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "SEM_PERMISSAO"


@pytest.mark.parametrize(
    ("perfil", "ativo"),
    [
        (PerfilUsuario.ATENDENTE, True),
        (PerfilUsuario.GERENTE, True),
        (PerfilUsuario.MECANICO, False),
    ],
)
async def test_gerente_so_atribui_a_mecanico_ativo(
    cliente_http, conexao, gerente, os_recebida, perfil, ativo
):
    indicado = await _inserir_usuario(conexao, perfil, ativo)

    resposta = await _atribuir(
        cliente_http, gerente, os_recebida["id"], {"mecanico_id": str(indicado.id)}
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"


async def test_mecanico_inexistente_responde_404(cliente_http, gerente, os_recebida):
    resposta = await _atribuir(
        cliente_http, gerente, os_recebida["id"], {"mecanico_id": str(uuid4())}
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


async def test_os_inexistente_responde_404(cliente_http, mecanico):
    resposta = await _atribuir(cliente_http, mecanico, str(uuid4()))

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


async def test_os_fora_de_recebida_responde_422_e_nao_muda(
    cliente_http, conexao, mecanico, os_recebida
):
    outro = await _inserir_usuario(conexao, PerfilUsuario.MECANICO)
    await _atribuir(cliente_http, mecanico, os_recebida["id"])

    resposta = await _atribuir(cliente_http, outro, os_recebida["id"])

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "REGRA_DE_NEGOCIO_VIOLADA"
    mecanico_da_os = await conexao.scalar(
        text("SELECT mecanico_id FROM ordens_servico WHERE id = :id"), {"id": os_recebida["id"]}
    )
    assert mecanico_da_os == mecanico.id
    total = await conexao.scalar(
        text("SELECT count(*) FROM historico_status_os WHERE os_id = :id"),
        {"id": os_recebida["id"]},
    )
    assert total == 2


async def test_mecanico_id_que_nao_e_uuid_responde_422(cliente_http, gerente, os_recebida):
    resposta = await _atribuir(cliente_http, gerente, os_recebida["id"], {"mecanico_id": "abc"})

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "ENTRADA_INVALIDA"


async def test_atendente_nao_atribui_mecanico(cliente_http, atendente, mecanico, os_recebida):
    resposta = await _atribuir(
        cliente_http, atendente, os_recebida["id"], {"mecanico_id": str(mecanico.id)}
    )

    assert resposta.status_code == 403


async def test_sem_token_responde_401(cliente_http, os_recebida):
    resposta = await cliente_http.post(f"/ordens-servico/{os_recebida['id']}/mecanico")

    assert resposta.status_code == 401
