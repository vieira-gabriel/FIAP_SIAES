from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from domain.entities.historico_status_os import HistoricoStatusOS
from domain.exceptions import OrdemServicoInvalida, ValorInvalido
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS

AGORA = datetime.now(UTC)


def criar_registro(**alteracoes) -> HistoricoStatusOS:
    dados = {
        "status_anterior": StatusOS.RECEBIDA,
        "status_novo": StatusOS.EM_DIAGNOSTICO,
        "data_hora": AGORA,
        "origem": OrigemTransicao.USUARIO,
        "usuario_id": uuid4(),
    }
    dados.update(alteracoes)
    return HistoricoStatusOS(**dados)


def test_registra_a_transicao_feita_por_um_usuario():
    usuario_id = uuid4()

    registro = criar_registro(usuario_id=usuario_id)

    assert registro.status_anterior is StatusOS.RECEBIDA
    assert registro.status_novo is StatusOS.EM_DIAGNOSTICO
    assert registro.data_hora == AGORA
    assert registro.origem is OrigemTransicao.USUARIO
    assert registro.usuario_id == usuario_id
    assert registro.motivo is None


def test_registro_de_abertura_nao_tem_status_anterior():
    registro = criar_registro(status_anterior=None, status_novo=StatusOS.RECEBIDA)

    assert registro.status_anterior is None


@pytest.mark.parametrize("origem", [OrigemTransicao.CLIENTE, OrigemTransicao.SISTEMA])
def test_transicao_do_cliente_ou_do_sistema_nao_tem_usuario(origem):
    registro = criar_registro(origem=origem, usuario_id=None)

    assert registro.origem is origem
    assert registro.usuario_id is None


def test_transicao_feita_por_usuario_exige_o_usuario():
    with pytest.raises(OrdemServicoInvalida) as erro:
        criar_registro(origem=OrigemTransicao.USUARIO, usuario_id=None)

    assert isinstance(erro.value, ValorInvalido)


@pytest.mark.parametrize("origem", [OrigemTransicao.CLIENTE, OrigemTransicao.SISTEMA])
def test_transicao_do_cliente_ou_do_sistema_nao_aceita_usuario(origem):
    with pytest.raises(OrdemServicoInvalida):
        criar_registro(origem=origem, usuario_id=uuid4())


def test_recusa_status_novo_igual_ao_anterior():
    with pytest.raises(OrdemServicoInvalida):
        criar_registro(status_anterior=StatusOS.RECEBIDA, status_novo=StatusOS.RECEBIDA)


@pytest.mark.parametrize(
    "alteracao",
    [
        {"status_novo": "EM_DIAGNOSTICO"},
        {"status_novo": None},
        {"status_anterior": "RECEBIDA"},
        {"data_hora": "2026-10-27"},
        {"data_hora": datetime(2026, 10, 27, 12, 0)},
        {"origem": "USUARIO"},
        {"origem": "CLIENTE", "usuario_id": None},
        {"origem": "SISTEMA", "usuario_id": None},
        {"usuario_id": "nao-e-uuid"},
        {"motivo": 123},
    ],
    ids=[
        "status novo texto",
        "status novo nulo",
        "status anterior texto",
        "data texto",
        "data sem fuso",
        "origem texto com usuario",
        "origem cliente em texto, sem usuario",
        "origem sistema em texto, sem usuario",
        "usuario que nao e uuid",
        "motivo que nao e texto",
    ],
)
def test_recusa_dados_do_tipo_errado(alteracao):
    with pytest.raises(OrdemServicoInvalida):
        criar_registro(**alteracao)


def test_guarda_o_motivo_sem_espacos_nas_pontas():
    registro = criar_registro(motivo="  Cliente desistiu do serviço  ")

    assert registro.motivo == "Cliente desistiu do serviço"


@pytest.mark.parametrize("motivo", ["", "   "])
def test_motivo_em_branco_vira_ausente(motivo):
    assert criar_registro(motivo=motivo).motivo is None


def test_o_registro_nao_pode_ser_alterado_depois_de_criado():
    registro = criar_registro(motivo="Motivo original")

    with pytest.raises(FrozenInstanceError):
        registro.status_novo = StatusOS.CANCELADA
    with pytest.raises(FrozenInstanceError):
        registro.motivo = "Outro motivo"
    with pytest.raises(FrozenInstanceError):
        del registro.usuario_id

    assert registro.status_novo is StatusOS.EM_DIAGNOSTICO
    assert registro.motivo == "Motivo original"


def test_cada_registro_tem_o_proprio_identificador():
    assert criar_registro().id != criar_registro().id
