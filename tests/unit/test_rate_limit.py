import pytest

from presentation.middlewares import rate_limit


def test_limite_so_existe_depois_de_configurado(monkeypatch):
    monkeypatch.setattr(rate_limit, "_limite_publico", None)

    with pytest.raises(RuntimeError):
        rate_limit._limite_configurado()


def test_configurar_guarda_o_limite(monkeypatch):
    monkeypatch.setattr(rate_limit, "_limite_publico", None)

    rate_limit.configurar_limite_publico("5/minute")

    assert rate_limit._limite_configurado() == "5/minute"


def test_limite_malformado_nao_substitui_o_anterior(monkeypatch):
    monkeypatch.setattr(rate_limit, "_limite_publico", "5/minute")

    with pytest.raises(ValueError):
        rate_limit.configurar_limite_publico("lixo")

    assert rate_limit._limite_configurado() == "5/minute"
