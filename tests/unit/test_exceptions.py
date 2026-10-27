from uuid import uuid4

import pytest

from domain.exceptions import (
    CNPJInvalido,
    CPFInvalido,
    CredenciaisInvalidas,
    EntidadeNaoEncontrada,
    ErroDeDominio,
    ItensBloqueados,
    MotivoObrigatorio,
    NumeroOSInvalido,
    PlacaInvalida,
    RegraDeNegocioViolada,
    SaldoInsuficiente,
    TransicaoDeStatusInvalida,
    UsuarioInvalido,
    ValorInvalido,
)
from domain.value_objects.status_os import StatusOS


@pytest.mark.parametrize("base", [EntidadeNaoEncontrada, RegraDeNegocioViolada, ValorInvalido])
def test_bases_herdam_de_erro_de_dominio(base):
    assert issubclass(base, ErroDeDominio)


@pytest.mark.parametrize(
    ("excecao", "base"),
    [
        (CPFInvalido(), ValorInvalido),
        (CNPJInvalido(), ValorInvalido),
        (PlacaInvalida("ABC-1234"), ValorInvalido),
        (NumeroOSInvalido("123-abc"), ValorInvalido),
        (UsuarioInvalido("o nome é obrigatório"), ValorInvalido),
        (
            TransicaoDeStatusInvalida(StatusOS.RECEBIDA, StatusOS.FINALIZADA),
            RegraDeNegocioViolada,
        ),
        (SaldoInsuficiente("Filtro de óleo", 3, 1), RegraDeNegocioViolada),
        (ItensBloqueados(StatusOS.FINALIZADA), RegraDeNegocioViolada),
        (MotivoObrigatorio(), RegraDeNegocioViolada),
    ],
)
def test_especificas_herdam_da_base_correta(excecao, base):
    assert isinstance(excecao, base)


def test_bases_sao_disjuntas():
    bases = [EntidadeNaoEncontrada, RegraDeNegocioViolada, ValorInvalido]

    for base in bases:
        for outra in bases:
            if base is not outra:
                assert not issubclass(base, outra)


def test_credenciais_invalidas_fica_fora_das_bases_de_400_404_422():
    excecao = CredenciaisInvalidas()

    assert isinstance(excecao, ErroDeDominio)
    assert not isinstance(excecao, EntidadeNaoEncontrada | RegraDeNegocioViolada | ValorInvalido)


def test_transicao_invalida_informa_status_atual_e_pretendido():
    excecao = TransicaoDeStatusInvalida(StatusOS.RECEBIDA, StatusOS.FINALIZADA)

    assert excecao.status_atual is StatusOS.RECEBIDA
    assert excecao.status_pretendido is StatusOS.FINALIZADA
    assert str(excecao) == "Transição de status inválida: RECEBIDA → FINALIZADA."


def test_saldo_insuficiente_informa_peca_e_quantidades():
    excecao = SaldoInsuficiente("Filtro de óleo", 3, 1)

    assert (excecao.peca, excecao.quantidade_solicitada, excecao.saldo_disponivel) == (
        "Filtro de óleo",
        3,
        1,
    )
    assert str(excecao) == "Saldo insuficiente da peça Filtro de óleo: solicitado 3, disponível 1."


def test_entidade_nao_encontrada_informa_entidade_e_identificador():
    identificador = uuid4()

    excecao = EntidadeNaoEncontrada("Cliente", identificador)

    assert excecao.entidade == "Cliente"
    assert excecao.identificador == identificador
    assert str(identificador) in str(excecao)


def test_placa_invalida_informa_a_placa():
    excecao = PlacaInvalida("ABC-1234")

    assert excecao.placa == "ABC-1234"
    assert "ABC-1234" in str(excecao)


@pytest.mark.parametrize(
    ("excecao", "documento"),
    [(CPFInvalido(), "CPF"), (CNPJInvalido(), "CNPJ")],
)
def test_documento_invalido_nao_expoe_o_numero(excecao, documento):
    assert str(excecao) == f"{documento} inválido."


def test_itens_bloqueados_informa_o_status():
    excecao = ItensBloqueados(StatusOS.FINALIZADA)

    assert excecao.status_atual is StatusOS.FINALIZADA
    assert "FINALIZADA" in str(excecao)


def test_motivo_obrigatorio_tem_mensagem():
    assert str(MotivoObrigatorio()) == "Informe o motivo do cancelamento."
