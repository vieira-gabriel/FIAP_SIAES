"""Entrega do veículo pela rota HTTP, com PostgreSQL real (RF-22, RF-24)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from domain.entities.usuario import Usuario
from domain.value_objects.perfil_usuario import PerfilUsuario
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
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


async def _os_com_orcamento(cliente_http, atendente, mecanico, gerente) -> str:
    """Abre a OS, o mecânico a assume, inclui um serviço e conclui o orçamento."""
    servico = await cliente_http.post("/servicos", json=SERVICO, headers=_cabecalho(gerente))
    aberta = await cliente_http.post(
        "/ordens-servico", json=ABERTURA, headers=_cabecalho(atendente)
    )
    os_id = aberta.json()["id"]
    await cliente_http.post(f"/ordens-servico/{os_id}/mecanico", headers=_cabecalho(mecanico))
    await cliente_http.post(
        f"/ordens-servico/{os_id}/servicos",
        json={"servico_id": servico.json()["id"]},
        headers=_cabecalho(mecanico),
    )
    resposta = await cliente_http.post(
        f"/ordens-servico/{os_id}/orcamento", headers=_cabecalho(mecanico)
    )
    assert resposta.status_code == 200
    return os_id


async def _finalizar(cliente_http, fabrica_de_sessoes, os_id: str, mecanico: Usuario) -> None:
    """A rota de aprovação do cliente é a issue #98; aqui a aprovação usa o domínio."""
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        ordens = PostgresOrdemServicoRepository(unidade.sessao)
        os = await ordens.buscar_por_id(UUID(os_id))
        os.aprovar_orcamento()
        await ordens.salvar(os)
    for rota in ("execucao", "conclusao"):
        resposta = await cliente_http.post(
            f"/ordens-servico/{os_id}/{rota}", headers=_cabecalho(mecanico)
        )
        assert resposta.status_code == 200


@pytest.fixture
async def os_finalizada(cliente_http, atendente, mecanico, gerente, fabrica_de_sessoes) -> str:
    os_id = await _os_com_orcamento(cliente_http, atendente, mecanico, gerente)
    await _finalizar(cliente_http, fabrica_de_sessoes, os_id, mecanico)
    return os_id


async def _entregar(cliente_http, quem, os_id: str):
    return await cliente_http.post(f"/ordens-servico/{os_id}/entrega", headers=_cabecalho(quem))


async def _detalhe(cliente_http, quem, os_id: str) -> dict:
    return (await cliente_http.get(f"/ordens-servico/{os_id}", headers=_cabecalho(quem))).json()


async def test_atendente_entrega_o_veiculo_e_o_historico_registra_a_transicao(
    cliente_http, atendente, os_finalizada
):
    resposta = await _entregar(cliente_http, atendente, os_finalizada)

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ENTREGUE"
    registro = (await _detalhe(cliente_http, atendente, os_finalizada))["historico"][-1]
    assert (registro["status_anterior"], registro["status_novo"], registro["origem"]) == (
        "FINALIZADA",
        "ENTREGUE",
        "USUARIO",
    )
    assert registro["usuario_id"] == str(atendente.id)


async def test_gerente_tambem_entrega(cliente_http, gerente, os_finalizada):
    resposta = await _entregar(cliente_http, gerente, os_finalizada)

    assert resposta.status_code == 200


async def test_mecanico_recebe_403_e_a_os_continua_finalizada(
    cliente_http, atendente, mecanico, os_finalizada
):
    resposta = await _entregar(cliente_http, mecanico, os_finalizada)

    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "SEM_PERMISSAO")
    assert (await _detalhe(cliente_http, atendente, os_finalizada))["status"] == "FINALIZADA"


async def test_entrega_de_os_ainda_nao_finalizada_responde_422(
    cliente_http, atendente, mecanico, gerente
):
    os_id = await _os_com_orcamento(cliente_http, atendente, mecanico, gerente)

    resposta = await _entregar(cliente_http, atendente, os_id)

    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "REGRA_DE_NEGOCIO_VIOLADA")


async def test_entregar_duas_vezes_responde_422_na_segunda(cliente_http, atendente, os_finalizada):
    primeira = await _entregar(cliente_http, atendente, os_finalizada)
    segunda = await _entregar(cliente_http, atendente, os_finalizada)

    assert (primeira.status_code, segunda.status_code) == (200, 422)


async def test_entrega_de_os_inexistente_responde_404(cliente_http, atendente):
    assert (await _entregar(cliente_http, atendente, str(uuid4()))).status_code == 404
