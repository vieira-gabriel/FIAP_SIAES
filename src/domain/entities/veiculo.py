from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from domain.exceptions import VeiculoInvalido
from domain.value_objects.placa import Placa

ANO_MINIMO = 1900


@dataclass(eq=False)
class Veiculo:
    """Veículo vinculado ao cliente proprietário (RF-07 a RF-09)."""

    cliente_id: UUID
    placa: Placa
    marca: str
    modelo: str
    ano: int
    ativo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        if not isinstance(self.cliente_id, UUID):
            raise VeiculoInvalido("o cliente proprietário é obrigatório")
        self._aplicar_dados(self.placa, self.marca, self.modelo, self.ano)

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, Veiculo) and outro.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def atualizar_dados(self, placa: Placa, marca: str, modelo: str, ano: int) -> None:
        self._aplicar_dados(placa, marca, modelo, ano)

    def excluir(self) -> None:
        """Exclusão lógica: as ordens de serviço do veículo continuam no histórico (RF-09)."""
        self.ativo = False

    def _aplicar_dados(self, placa: Placa, marca: str, modelo: str, ano: int) -> None:
        marca = marca.strip()
        modelo = modelo.strip()
        if not isinstance(placa, Placa):
            raise VeiculoInvalido("a placa é obrigatória")
        if not marca:
            raise VeiculoInvalido("a marca é obrigatória")
        if not modelo:
            raise VeiculoInvalido("o modelo é obrigatório")
        _validar_ano(ano)
        self.placa, self.marca, self.modelo, self.ano = placa, marca, modelo, ano


def _validar_ano(ano: int) -> None:
    # O ano seguinte é aceito porque os modelos do próximo ano chegam às lojas antes dele.
    ano_maximo = date.today().year + 1
    if type(ano) is not int or not ANO_MINIMO <= ano <= ano_maximo:
        raise VeiculoInvalido(f"o ano de fabricação deve estar entre {ANO_MINIMO} e {ano_maximo}")
