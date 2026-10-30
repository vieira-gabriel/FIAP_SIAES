"""Detalhamento da OS pela rota HTTP, com PostgreSQL real (RF-15, RF-24, RF-25, RNF-13)."""

from uuid import uuid4

import pytest

from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from infrastructure.database.unidade_de_trabalho import UnidadeDeTrabalhoSqlAlchemy
from infrastructure.repositories.postgres_cliente_repository import PostgresClienteRepository
from infrastructure.repositories.postgres_ordem_servico_repository import (
    PostgresOrdemServicoRepository,
)
from infrastructure.repositories.postgres_peca_repository import PostgresPecaRepository
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.repositories.postgres_veiculo_repository import PostgresVeiculoRepository
from presentation.main import app

PECA = {
    "codigo_referencia": "FLT-001",
    "nome": "Filtro de óleo",
    "preco_unitario": "35.90",
    "prazo_reposicao_dias": 3,
}


def _cabecalho(perfil: PerfilUsuario) -> dict[str, str]:
    usuario = Usuario(nome="Qualquer", email="q@oficina.com", senha_hash="h", perfil=perfil)
    return {"Authorization": f"Bearer {app.state.token_service.emitir(usuario)}"}


async def _os_aguardando_peca(fabrica_de_sessoes, peca_id) -> str:
    """OS com uma peça que não tem saldo: após o orçamento e a aprovação, fica em
    `AGUARDANDO_PECA` com a peça pendente."""
    atendente = Usuario(
        nome="Ana",
        email=f"ana-{uuid4().hex[:6]}@oficina.com",
        senha_hash="h",
        perfil=PerfilUsuario.ATENDENTE,
    )
    cliente = Cliente(
        nome="Carla", documento=CPF("529.982.247-25"), email="c@email.com", telefone="1199999"
    )
    veiculo = Veiculo(
        cliente_id=cliente.id, placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2020
    )
    async with UnidadeDeTrabalhoSqlAlchemy(fabrica_de_sessoes) as unidade:
        sessao = unidade.sessao
        await PostgresUsuarioRepository(sessao).salvar(atendente)
        await PostgresClienteRepository(sessao).salvar(cliente)
        await sessao.flush()
        await PostgresVeiculoRepository(sessao).salvar(veiculo)
        await sessao.flush()
        peca = await PostgresPecaRepository(sessao).buscar_por_id(peca_id)
        os = OrdemServico.abrir(
            numero=NumeroOS.gerar(CPF("529.982.247-25"), uuid4()),
            cliente_id=cliente.id,
            veiculo_id=veiculo.id,
            atendente_id=atendente.id,
        )
        os.atribuir_mecanico(atendente.id)
        os.incluir_peca(peca, quantidade=1)
        os.finalizar_orcamento(atendente.id, [], [peca])
        os.aprovar_orcamento()
        await PostgresOrdemServicoRepository(sessao).salvar(os)
    return str(os.id)


async def test_detalha_os_em_aguardando_peca_com_pendentes(cliente_http, fabrica_de_sessoes):
    gerente = _cabecalho(PerfilUsuario.GERENTE)
    peca = (
        await cliente_http.post(
            "/pecas", json=PECA | {"quantidade_fisica_inicial": 0}, headers=gerente
        )
    ).json()
    os_id = await _os_aguardando_peca(fabrica_de_sessoes, peca["id"])

    resposta = await cliente_http.get(
        f"/ordens-servico/{os_id}", headers=_cabecalho(PerfilUsuario.MECANICO)
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "AGUARDANDO_PECA"
    assert corpo["cliente"]["nome"] == "Carla"
    assert corpo["veiculo"]["placa"] == "ABC1D23"
    assert corpo["pecas"][0]["quantidade_pendente"] == 1
    assert corpo["pecas"][0]["quantidade_reservada"] == 0
    assert corpo["pecas"][0]["preco_unitario_congelado"] == "35.90"
    assert corpo["orcamento"]["total"] == "35.90"
    assert [r["status_novo"] for r in corpo["historico"]][-1] == "AGUARDANDO_PECA"
    assert len(corpo["historico"]) >= 4


@pytest.mark.parametrize(
    "perfil", [PerfilUsuario.ATENDENTE, PerfilUsuario.MECANICO, PerfilUsuario.GERENTE]
)
async def test_todos_os_perfis_consultam_a_os(cliente_http, fabrica_de_sessoes, perfil):
    gerente = _cabecalho(PerfilUsuario.GERENTE)
    peca = (
        await cliente_http.post(
            "/pecas", json=PECA | {"quantidade_fisica_inicial": 0}, headers=gerente
        )
    ).json()
    os_id = await _os_aguardando_peca(fabrica_de_sessoes, peca["id"])

    resposta = await cliente_http.get(f"/ordens-servico/{os_id}", headers=_cabecalho(perfil))

    assert resposta.status_code == 200


async def test_os_inexistente_responde_404(cliente_http):
    resposta = await cliente_http.get(
        f"/ordens-servico/{uuid4()}", headers=_cabecalho(PerfilUsuario.GERENTE)
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "ENTIDADE_NAO_ENCONTRADA"


async def test_sem_token_responde_401(cliente_http):
    assert (await cliente_http.get(f"/ordens-servico/{uuid4()}")).status_code == 401
