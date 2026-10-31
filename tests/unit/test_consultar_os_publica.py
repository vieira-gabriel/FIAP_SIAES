from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application.use_cases.consultar_os_publica import ConsultarOSPublica
from domain.entities.cliente import Cliente
from domain.entities.item_servico import ItemServico
from domain.entities.ordem_servico import OrdemServico
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.cnpj import CNPJ
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

MOMENTO = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
NUMERO = "529-7F3A9C2B"


@pytest.fixture
def consultar(ordens, clientes) -> ConsultarOSPublica:
    return ConsultarOSPublica(ordens, clientes)


async def _os_do_cliente(clientes, ordens, documento=None, **alteracoes) -> OrdemServico:
    cliente = Cliente(
        nome="Maria", documento=documento or CPF("52998224725"), email="m@e.com", telefone="11"
    )
    await clientes.salvar(cliente)
    dados = {
        "numero": NumeroOS(NUMERO),
        "cliente_id": cliente.id,
        "veiculo_id": uuid4(),
        "atendente_id": uuid4(),
    }
    os = OrdemServico(**(dados | alteracoes))
    await ordens.salvar(os)
    return os


async def test_devolve_a_os_do_titular_com_a_estimativa_de_entrega(consultar, clientes, ordens):
    servico = ItemServico(
        servico_id=uuid4(),
        nome="Troca de óleo",
        preco_congelado=Valor("120.00"),
        tempo_estimado_minutos=60,
    )
    os = await _os_do_cliente(
        clientes, ordens, status=StatusOS.AGUARDANDO_EXECUCAO, servicos=[servico]
    )

    acompanhamento = await consultar.executar(NUMERO, "529.982.247-25", MOMENTO)

    assert acompanhamento.os == os
    assert acompanhamento.estimativa_entrega == MOMENTO + timedelta(hours=1)


@pytest.mark.parametrize("documento", ["529.982.247-25", "52998224725", " 529.982.247-25 "])
async def test_aceita_o_documento_com_ou_sem_pontuacao(consultar, clientes, ordens, documento):
    os = await _os_do_cliente(clientes, ordens)

    assert (await consultar.executar(NUMERO, documento, MOMENTO)).os == os


async def test_aceita_o_numero_em_minusculas_e_com_espacos(consultar, clientes, ordens):
    os = await _os_do_cliente(clientes, ordens)

    acompanhamento = await consultar.executar(" 529-7f3a9c2b ", "52998224725", MOMENTO)

    assert acompanhamento.os == os


async def test_titular_pessoa_juridica(consultar, clientes, ordens):
    os = await _os_do_cliente(clientes, ordens, documento=CNPJ("11222333000181"))

    acompanhamento = await consultar.executar(NUMERO, "11.222.333/0001-81", MOMENTO)

    assert acompanhamento.os == os


async def test_cliente_excluido_continua_consultando_a_propria_os(consultar, clientes, ordens):
    os = await _os_do_cliente(clientes, ordens)
    cliente = await clientes.buscar_por_id(os.cliente_id)
    cliente.excluir()
    await clientes.salvar(cliente)

    assert (await consultar.executar(NUMERO, "52998224725", MOMENTO)).os == os


async def test_os_cancelada_continua_consultavel_sem_estimativa(consultar, clientes, ordens):
    await _os_do_cliente(clientes, ordens, status=StatusOS.CANCELADA)

    acompanhamento = await consultar.executar(NUMERO, "52998224725", MOMENTO)

    assert acompanhamento.estimativa_entrega is None


@pytest.mark.parametrize(
    ("numero", "documento"),
    [
        ("123-AAAAAAAA", "52998224725"),
        (NUMERO, "11144477735"),
        (NUMERO, "11222333000181"),
        ("sem formato", "52998224725"),
        (NUMERO, "123"),
        (NUMERO, "529.982.247-26"),
        ("", ""),
    ],
    ids=[
        "numero inexistente",
        "cpf de outro titular",
        "cnpj de outro titular",
        "numero malformado",
        "documento malformado",
        "cpf com digito invalido",
        "tudo vazio",
    ],
)
async def test_todo_erro_de_identificacao_levanta_o_mesmo_erro(
    consultar, clientes, ordens, numero, documento
):
    await _os_do_cliente(clientes, ordens)
    referencia = await _erro_do_numero_inexistente(consultar)

    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await consultar.executar(numero, documento, MOMENTO)

    assert str(erro.value) == str(referencia)
    assert NUMERO not in str(erro.value)


async def _erro_do_numero_inexistente(consultar) -> EntidadeNaoEncontrada:
    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await consultar.executar("999-00000000", "52998224725", MOMENTO)
    return erro.value


async def test_os_sem_cliente_cadastrado_responde_como_nao_encontrada(consultar, ordens):
    await ordens.salvar(
        OrdemServico(
            numero=NumeroOS(NUMERO), cliente_id=uuid4(), veiculo_id=uuid4(), atendente_id=uuid4()
        )
    )

    with pytest.raises(EntidadeNaoEncontrada):
        await consultar.executar(NUMERO, "52998224725", MOMENTO)
