"""Cenário de desempenho da API (RNF-10): o p95 do tempo de resposta deve ficar abaixo de 500 ms.

Roda contra a aplicação no ar (`docker compose up --build`), com `ADMIN_PASSWORD` no ambiente.
O comando completo e o cenário estão em `docs/evidencias/desempenho.md`.

As rotas públicas de acompanhamento ficam fora do cenário: o limite de 10 requisições por minuto
por IP (RNF-05) responderia 429 a quase toda requisição de uma carga vinda de um só endereço.
"""

import os
import random

import requests
from locust import HttpUser, between, events, task

LIMITE_P95_MS = 500
QUANTIDADE_DE_OS = 30
EMAIL_DO_GERENTE = os.environ.get("ADMIN_EMAIL", "admin@oficina.com")
SENHA_DO_GERENTE = os.environ.get("ADMIN_PASSWORD", "")

_TITULARES: list[dict[str, str]] = []
_IDS_DAS_OS: list[str] = []


def _cpf(numero: int) -> str:
    """CPF válido e distinto para cada número, para abrir uma OS por cliente."""
    digitos = [int(d) for d in f"{100_000_000 + numero * 7_919:09d}"[-9:]]
    for tamanho in (9, 10):
        soma = sum(d * (tamanho + 1 - i) for i, d in enumerate(digitos[:tamanho]))
        digitos.append((soma * 10 % 11) % 10)
    return "".join(str(d) for d in digitos)


def _placa(numero: int) -> str:
    letras = [chr(ord("A") + (numero // 26**posicao) % 26) for posicao in (2, 1, 0)]
    return f"{''.join(letras)}1A23"


def _cabecalho(host: str) -> dict[str, str]:
    resposta = requests.post(
        f"{host}/auth/login",
        json={"email": EMAIL_DO_GERENTE, "senha": SENHA_DO_GERENTE},
        timeout=30,
    )
    resposta.raise_for_status()
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@events.test_start.add_listener
def preparar_os_para_consultar(environment, **_):
    """Abre as OS que as consultas listam e detalham, para o banco não estar vazio."""
    host = environment.host
    cabecalho = _cabecalho(host)
    for numero in range(QUANTIDADE_DE_OS):
        titular = {"documento": _cpf(numero), "placa": _placa(numero)}
        corpo = titular | {
            "cliente": {
                "nome": f"Cliente de carga {numero}",
                "email": f"carga{numero}@exemplo.com",
                "telefone": "11987654321",
            },
            "veiculo": {"marca": "Fiat", "modelo": "Uno", "ano": 2015},
        }
        resposta = requests.post(
            f"{host}/ordens-servico", json=corpo, headers=cabecalho, timeout=30
        )
        if resposta.status_code == 201:
            _TITULARES.append(titular)
            _IDS_DAS_OS.append(resposta.json()["id"])
    if not _IDS_DAS_OS:
        environment.process_exit_code = 1
        raise SystemExit("Nenhuma OS foi aberta para o cenário: confira o host e a ADMIN_PASSWORD.")


@events.quitting.add_listener
def falhar_se_o_p95_passar_do_limite(environment, **_):
    total = environment.stats.total
    p95 = total.get_response_time_percentile(0.95)
    if total.num_failures or (p95 is not None and p95 > LIMITE_P95_MS):
        print(f"FALHA: p95 = {p95} ms (limite {LIMITE_P95_MS} ms), {total.num_failures} erros")
        environment.process_exit_code = 1
    else:
        print(f"OK: p95 = {p95} ms (limite {LIMITE_P95_MS} ms), sem erros")


class UsuarioDaOficina(HttpUser):
    """Usa a API como o Gerente: consulta cadastros e OS e abre OS novas."""

    wait_time = between(0.5, 1.5)

    def on_start(self):
        resposta = self.client.post(
            "/auth/login", json={"email": EMAIL_DO_GERENTE, "senha": SENHA_DO_GERENTE}
        )
        self.client.headers["Authorization"] = f"Bearer {resposta.json()['access_token']}"

    @task(5)
    def listar_ordens_de_servico(self):
        self.client.get("/ordens-servico", name="GET /ordens-servico")

    @task(2)
    def listar_ordens_por_status(self):
        self.client.get(
            "/ordens-servico", params={"status": "RECEBIDA"}, name="GET /ordens-servico?status"
        )

    @task(3)
    def detalhar_ordem_de_servico(self):
        os_id = random.choice(_IDS_DAS_OS)
        self.client.get(f"/ordens-servico/{os_id}", name="GET /ordens-servico/{id}")

    @task(1)
    def listar_pecas(self):
        self.client.get("/pecas", name="GET /pecas")

    @task(1)
    def listar_servicos(self):
        self.client.get("/servicos", name="GET /servicos")

    @task(1)
    def listar_clientes(self):
        self.client.get("/clientes", name="GET /clientes")

    @task(1)
    def abrir_ordem_de_servico(self):
        titular = random.choice(_TITULARES)
        self.client.post("/ordens-servico", json=titular, name="POST /ordens-servico")
