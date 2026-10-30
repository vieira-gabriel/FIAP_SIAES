from uuid import uuid4

import pytest

from application.use_cases import criar_os as modulo
from application.use_cases.criar_os import CriarOS, DadosDoNovoCliente, DadosDoNovoVeiculo
from domain.entities.cliente import Cliente
from domain.entities.ordem_servico import OrdemServico
from domain.entities.usuario import Usuario
from domain.entities.veiculo import Veiculo
from domain.exceptions import (
    DocumentoJaCadastrado,
    EntidadeNaoEncontrada,
    NumeroOSIndisponivel,
    OSDeOutroCliente,
)
from domain.value_objects.cpf import CPF
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa

ATENDENTE = Usuario(
    nome="Ana", email="ana@oficina.com", senha_hash="h", perfil=PerfilUsuario.ATENDENTE
)
CPF_MARIA = "529.982.247-25"
NOVO_CLIENTE = DadosDoNovoCliente(nome="Maria", email="m@exemplo.com", telefone="11")
NOVO_VEICULO = DadosDoNovoVeiculo(marca="Fiat", modelo="Uno", ano=2015)


def _caso(clientes, veiculos, ordens):
    return CriarOS(clientes, veiculos, ordens)


async def _cliente_existente(clientes, documento=CPF_MARIA) -> Cliente:
    cliente = Cliente(nome="Maria", documento=CPF(documento), email="m@exemplo.com", telefone="11")
    await clientes.salvar(cliente)
    return cliente


async def test_abre_os_com_cliente_e_veiculo_existentes(clientes, veiculos, ordens):
    cliente = await _cliente_existente(clientes)
    veiculo = Veiculo(
        cliente_id=cliente.id, placa=Placa("ABC1D23"), marca="Fiat", modelo="Uno", ano=2015
    )
    await veiculos.salvar(veiculo)

    os = await _caso(clientes, veiculos, ordens).executar(
        CPF(CPF_MARIA), Placa("abc-1d23"), ATENDENTE.id
    )

    assert os.status.value == "RECEBIDA"
    assert (os.cliente_id, os.veiculo_id, os.atendente_id) == (cliente.id, veiculo.id, ATENDENTE.id)
    assert await ordens.buscar_por_id(os.id) == os
    assert len(clientes.dados) == 1 and len(veiculos.dados) == 1


async def test_cadastra_cliente_e_veiculo_no_mesmo_fluxo(clientes, veiculos, ordens):
    os = await _caso(clientes, veiculos, ordens).executar(
        CPF(CPF_MARIA),
        Placa("ABC1234"),
        ATENDENTE.id,
        cliente_novo=NOVO_CLIENTE,
        veiculo_novo=NOVO_VEICULO,
    )

    cliente = await clientes.buscar_por_documento(CPF(CPF_MARIA))
    veiculo = await veiculos.buscar_por_placa(Placa("ABC1234"))
    assert os.cliente_id == cliente.id
    assert os.veiculo_id == veiculo.id
    assert veiculo.cliente_id == cliente.id


async def test_cliente_inexistente_sem_dados_responde_404(clientes, veiculos, ordens):
    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await _caso(clientes, veiculos, ordens).executar(
            CPF(CPF_MARIA), Placa("ABC1234"), ATENDENTE.id, veiculo_novo=NOVO_VEICULO
        )

    assert erro.value.entidade == "Cliente"
    assert ordens.dados == {}


async def test_veiculo_inexistente_sem_dados_responde_404(clientes, veiculos, ordens):
    await _cliente_existente(clientes)

    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await _caso(clientes, veiculos, ordens).executar(
            CPF(CPF_MARIA), Placa("ABC1234"), ATENDENTE.id
        )

    assert erro.value.entidade == "Veículo"


async def test_placa_de_veiculo_de_outro_cliente_e_recusada(clientes, veiculos, ordens):
    dona = await _cliente_existente(clientes, "111.444.777-35")
    await veiculos.salvar(
        Veiculo(cliente_id=dona.id, placa=Placa("ABC1234"), marca="Fiat", modelo="Uno", ano=2015)
    )
    await _cliente_existente(clientes)

    with pytest.raises(OSDeOutroCliente):
        await _caso(clientes, veiculos, ordens).executar(
            CPF(CPF_MARIA), Placa("ABC1234"), ATENDENTE.id
        )

    assert ordens.dados == {}


async def test_documento_de_cliente_excluido_nao_e_recadastrado_na_abertura(
    clientes, veiculos, ordens
):
    excluido = await _cliente_existente(clientes)
    excluido.excluir()

    with pytest.raises(DocumentoJaCadastrado):
        await _caso(clientes, veiculos, ordens).executar(
            CPF(CPF_MARIA),
            Placa("ABC1234"),
            ATENDENTE.id,
            cliente_novo=NOVO_CLIENTE,
            veiculo_novo=NOVO_VEICULO,
        )


async def test_colisao_de_numero_gera_novo_uuid(clientes, veiculos, ordens, monkeypatch):
    cliente = await _cliente_existente(clientes)
    await veiculos.salvar(
        Veiculo(cliente_id=cliente.id, placa=Placa("ABC1234"), marca="F", modelo="U", ano=2015)
    )
    primeiro, segundo = uuid4(), uuid4()
    sorteios = iter([primeiro, segundo])
    monkeypatch.setattr(modulo, "uuid4", lambda: next(sorteios))
    colidido = OrdemServico.abrir(
        numero=NumeroOS.gerar(CPF(CPF_MARIA), primeiro),
        cliente_id=cliente.id,
        veiculo_id=uuid4(),
        atendente_id=ATENDENTE.id,
    )
    await ordens.salvar(colidido)

    os = await _caso(clientes, veiculos, ordens).executar(
        CPF(CPF_MARIA), Placa("ABC1234"), ATENDENTE.id
    )

    assert os.id == segundo
    assert os.numero == NumeroOS.gerar(CPF(CPF_MARIA), segundo)


async def test_sem_numero_livre_apos_as_tentativas_responde_erro(
    clientes, veiculos, ordens, monkeypatch
):
    cliente = await _cliente_existente(clientes)
    await veiculos.salvar(
        Veiculo(cliente_id=cliente.id, placa=Placa("ABC1234"), marca="F", modelo="U", ano=2015)
    )

    async def sempre_ocupado(numero):
        return object()

    monkeypatch.setattr(ordens, "buscar_por_numero", sempre_ocupado)

    with pytest.raises(NumeroOSIndisponivel):
        await _caso(clientes, veiculos, ordens).executar(
            CPF(CPF_MARIA), Placa("ABC1234"), ATENDENTE.id
        )
