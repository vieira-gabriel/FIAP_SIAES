from uuid import uuid4

import pytest

from domain.entities.cliente import Cliente
from domain.exceptions import DocumentoJaCadastrado, EntidadeNaoEncontrada
from domain.repositories.cliente_repository import ClienteRepository
from domain.value_objects.cpf import CPF


def test_porta_define_salvar_buscas_e_listagem():
    assert ClienteRepository.__abstractmethods__ == {
        "salvar",
        "buscar_por_id",
        "buscar_por_documento",
        "listar",
    }


def test_implementacao_incompleta_nao_pode_ser_criada():
    class SemBuscaPorDocumento(ClienteRepository):
        async def salvar(self, cliente): ...

        async def buscar_por_id(self, id): ...

        async def listar(self): ...

    with pytest.raises(TypeError):
        SemBuscaPorDocumento()


async def test_busca_por_documento_independe_da_pontuacao_digitada(clientes):
    repositorio = clientes
    cliente = Cliente(
        nome="Maria Silva",
        documento=CPF("529.982.247-25"),
        email="maria@exemplo.com",
        telefone="11987654321",
    )
    await repositorio.salvar(cliente)

    assert await repositorio.buscar_por_documento(CPF("52998224725")) == cliente
    assert await repositorio.buscar_por_id(cliente.id) == cliente
    assert await repositorio.buscar_por_documento(CPF("111.444.777-35")) is None


def _cliente(nome="Maria Silva", documento="529.982.247-25"):
    return Cliente(
        nome=nome,
        documento=CPF(documento),
        email="maria@exemplo.com",
        telefone="11987654321",
    )


async def test_buscar_ativo_por_id_devolve_o_cliente_ativo(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)

    assert await clientes.buscar_ativo_por_id(cliente.id) == cliente


async def test_buscar_ativo_por_id_trata_o_cliente_excluido_como_inexistente(clientes):
    cliente = _cliente()
    cliente.excluir()
    await clientes.salvar(cliente)

    with pytest.raises(EntidadeNaoEncontrada) as erro:
        await clientes.buscar_ativo_por_id(cliente.id)

    assert erro.value.entidade == "Cliente"


async def test_buscar_ativo_por_id_inexistente(clientes):
    with pytest.raises(EntidadeNaoEncontrada):
        await clientes.buscar_ativo_por_id(uuid4())


async def test_documento_de_outro_cliente_nao_esta_livre_mesmo_excluido(clientes):
    excluido = _cliente()
    excluido.excluir()
    await clientes.salvar(excluido)

    with pytest.raises(DocumentoJaCadastrado):
        await clientes.garantir_documento_livre(_cliente(nome="Outra Pessoa"))


async def test_o_proprio_documento_continua_livre_para_o_dono(clientes):
    cliente = _cliente()
    await clientes.salvar(cliente)

    await clientes.garantir_documento_livre(cliente)
