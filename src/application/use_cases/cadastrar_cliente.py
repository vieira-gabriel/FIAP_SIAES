from domain.entities.cliente import Cliente
from domain.repositories.cliente_repository import ClienteRepository
from domain.value_objects.documento import Documento


class CadastrarCliente:
    """Cadastro de cliente pessoa física ou jurídica (RF-04, RF-05)."""

    def __init__(self, clientes: ClienteRepository):
        self._clientes = clientes

    async def executar(self, nome: str, documento: Documento, email: str, telefone: str) -> Cliente:
        cliente = Cliente(nome=nome, documento=documento, email=email, telefone=telefone)
        await self._clientes.garantir_documento_livre(cliente)
        await self._clientes.salvar(cliente)
        return cliente
