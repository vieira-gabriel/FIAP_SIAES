import pytest

from application.ports.unidade_de_trabalho import UnidadeDeTrabalho


class UnidadeDeTrabalhoFalsa(UnidadeDeTrabalho):
    def __init__(self, falha_ao_confirmar: Exception | None = None):
        self.chamadas: list[str] = []
        self._falha_ao_confirmar = falha_ao_confirmar

    async def confirmar(self):
        self.chamadas.append("confirmar")
        if self._falha_ao_confirmar is not None:
            raise self._falha_ao_confirmar

    async def desfazer(self):
        self.chamadas.append("desfazer")


async def test_bloco_sem_excecao_confirma_e_nao_desfaz():
    unidade = UnidadeDeTrabalhoFalsa()

    async with unidade:
        pass

    assert unidade.chamadas == ["confirmar"]


async def test_excecao_no_bloco_desfaz_e_nao_confirma():
    unidade = UnidadeDeTrabalhoFalsa()

    with pytest.raises(RuntimeError):
        async with unidade:
            raise RuntimeError("falha no meio da operação")

    assert unidade.chamadas == ["desfazer"]


async def test_excecao_do_bloco_e_propagada_sem_alteracao():
    erro = ValueError("regra violada")

    with pytest.raises(ValueError) as capturado:
        async with UnidadeDeTrabalhoFalsa():
            raise erro

    assert capturado.value is erro


async def test_falha_ao_confirmar_desfaz_e_propaga():
    erro = RuntimeError("violação de integridade no commit")
    unidade = UnidadeDeTrabalhoFalsa(falha_ao_confirmar=erro)

    with pytest.raises(RuntimeError) as capturado:
        async with unidade:
            pass

    assert capturado.value is erro
    assert unidade.chamadas == ["confirmar", "desfazer"]


async def test_entrada_no_bloco_devolve_a_propria_unidade():
    unidade = UnidadeDeTrabalhoFalsa()

    async with unidade as dentro_do_bloco:
        assert dentro_do_bloco is unidade
