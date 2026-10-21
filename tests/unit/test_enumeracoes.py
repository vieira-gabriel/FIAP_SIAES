import pytest

from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.status_os import StatusOS


@pytest.mark.parametrize(
    ("enumeracao", "valores_da_linguagem_ubiqua"),
    [
        (
            StatusOS,
            [
                "RECEBIDA",
                "EM_DIAGNOSTICO",
                "AGUARDANDO_APROVACAO",
                "AGUARDANDO_PECA",
                "AGUARDANDO_EXECUCAO",
                "EM_EXECUCAO",
                "FINALIZADA",
                "ENTREGUE",
                "CANCELADA",
            ],
        ),
        (PerfilUsuario, ["ATENDENTE", "MECANICO", "GERENTE"]),
        (OrigemTransicao, ["USUARIO", "CLIENTE", "SISTEMA"]),
    ],
)
def test_valores_iguais_aos_da_linguagem_ubiqua(enumeracao, valores_da_linguagem_ubiqua):
    assert [membro.value for membro in enumeracao] == valores_da_linguagem_ubiqua
    assert all(membro.name == membro.value for membro in enumeracao)


@pytest.mark.parametrize("enumeracao", [StatusOS, PerfilUsuario, OrigemTransicao])
def test_valor_desconhecido_e_recusado(enumeracao):
    with pytest.raises(ValueError):
        enumeracao("DESCONHECIDO")


def test_membro_e_comparavel_com_o_texto_persistido():
    assert StatusOS("EM_EXECUCAO") is StatusOS.EM_EXECUCAO
    assert StatusOS.EM_EXECUCAO == "EM_EXECUCAO"
