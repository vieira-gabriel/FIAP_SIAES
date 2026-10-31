from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application.use_cases.detalhar_ordem_servico import DetalharOrdemServico
from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.veiculo import Veiculo
from domain.exceptions import EntidadeNaoEncontrada
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.placa import Placa

MOMENTO = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


async def _os_com_cliente_e_veiculo(clientes, veiculos, ordens, excluir_cliente=False):
    cliente = Cliente(nome="Maria", documento=CPF("52998224725"), email="m@e.com", telefone="11")
    veiculo = Veiculo(
        cliente_id=cliente.id, placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2015
    )
    await clientes.salvar(cliente)
    await veiculos.salvar(veiculo)
    os = OrdemServico.abrir(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=cliente.id,
        veiculo_id=veiculo.id,
        atendente_id=uuid4(),
    )
    await ordens.salvar(os)
    if excluir_cliente:
        cliente.excluir()
        await clientes.salvar(cliente)
    return os, cliente, veiculo


async def test_devolve_a_os_com_cliente_veiculo_e_historico(clientes, veiculos, ordens):
    os, cliente, veiculo = await _os_com_cliente_e_veiculo(clientes, veiculos, ordens)

    detalhe = await DetalharOrdemServico(ordens, clientes, veiculos).executar(os.id, MOMENTO)

    assert detalhe.os == os
    assert detalhe.cliente == cliente
    assert detalhe.veiculo == veiculo
    assert len(detalhe.os.historico) == 1


async def test_os_de_cliente_excluido_continua_detalhada(clientes, veiculos, ordens):
    os, cliente, _ = await _os_com_cliente_e_veiculo(
        clientes, veiculos, ordens, excluir_cliente=True
    )

    detalhe = await DetalharOrdemServico(ordens, clientes, veiculos).executar(os.id, MOMENTO)

    assert detalhe.cliente == cliente
    assert not detalhe.cliente.ativo


async def test_os_inexistente_responde_entidade_nao_encontrada(clientes, veiculos, ordens):
    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await DetalharOrdemServico(ordens, clientes, veiculos).executar(uuid4(), MOMENTO)

    assert erro.value.entidade == "Ordem de serviço"


async def test_estimativa_de_entrega_vem_do_momento_da_consulta(clientes, veiculos, ordens):
    os, _, _ = await _os_com_cliente_e_veiculo(clientes, veiculos, ordens)

    detalhe = await DetalharOrdemServico(ordens, clientes, veiculos).executar(os.id, MOMENTO)

    assert detalhe.estimativa_entrega == os.estimar_entrega(MOMENTO)
    assert detalhe.estimativa_entrega is None or detalhe.estimativa_entrega >= MOMENTO - timedelta(
        0
    )
