from uuid import uuid4

import pytest

from domain.entities.cliente import Cliente
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.exceptions import (
    ClienteInvalido,
    PecaInvalida,
    ServicoInvalido,
    UsuarioInvalido,
    ValorInvalido,
    VeiculoInvalido,
)
from domain.value_objects.cpf import CPF
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from domain.value_objects.texto_livre import exigir_sem_marcacao
from domain.value_objects.valor import Valor

SCRIPT = "<script>alert(1)</script>"


def test_texto_sem_marcacao_e_aceito_com_acentos_e_simbolos():
    exigir_sem_marcacao(ValorInvalido, nome="João & Filhos — \"Auto\" > 5 'peças'")


def test_texto_com_menor_que_e_recusado_com_o_nome_do_campo():
    with pytest.raises(ValorInvalido, match="o campo 'descricao'"):
        exigir_sem_marcacao(ValorInvalido, nome="Troca", descricao=SCRIPT)


def _cliente(**campos):
    dados = {"nome": "Maria", "documento": CPF("529.982.247-25"), "email": "m@e.com"}
    return Cliente(**{"telefone": "11987654321"} | dados | campos)


def _veiculo(**campos):
    dados = {"cliente_id": uuid4(), "placa": Placa("ABC1D23"), "marca": "Fiat", "modelo": "Uno"}
    return Veiculo(**{"ano": 2015} | dados | campos)


def _servico(**campos):
    dados = {"codigo": "SRV-1", "nome": "Troca", "descricao": "Troca de óleo"}
    return Servico(**{"valor_base": Valor("10.00"), "tempo_estimado_minutos": 30} | dados | campos)


def _peca(**campos):
    dados = {"codigo_referencia": "FO-1", "nome": "Filtro", "preco_unitario": Valor("5.00")}
    return Peca(**{"prazo_reposicao_dias": 1} | dados | campos)


def _usuario(**campos):
    dados = {"nome": "Ana", "email": "a@oficina.com", "senha_hash": "h"}
    return Usuario(**{"perfil": PerfilUsuario.ATENDENTE} | dados | campos)


@pytest.mark.parametrize(
    ("criar", "campo", "erro"),
    [
        (_cliente, "nome", ClienteInvalido),
        (_cliente, "email", ClienteInvalido),
        (_cliente, "telefone", ClienteInvalido),
        (_veiculo, "marca", VeiculoInvalido),
        (_veiculo, "modelo", VeiculoInvalido),
        (_servico, "codigo", ServicoInvalido),
        (_servico, "nome", ServicoInvalido),
        (_servico, "descricao", ServicoInvalido),
        (_peca, "codigo_referencia", PecaInvalida),
        (_peca, "nome", PecaInvalida),
        (_usuario, "nome", UsuarioInvalido),
        (_usuario, "email", UsuarioInvalido),
    ],
)
def test_campo_de_texto_livre_com_marcacao_e_recusado_na_criacao(criar, campo, erro):
    valor = f"a@{SCRIPT}.com" if campo == "email" else SCRIPT

    with pytest.raises(erro, match=f"o campo '{campo}'"):
        criar(**{campo: valor})


def test_atualizacao_com_marcacao_e_recusada_e_nao_altera_a_entidade():
    cliente = _cliente()

    with pytest.raises(ClienteInvalido):
        cliente.atualizar_dados(SCRIPT, cliente.documento, cliente.email, cliente.telefone)

    assert cliente.nome == "Maria"
