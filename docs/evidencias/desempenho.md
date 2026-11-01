# Evidência de Desempenho (RNF-10)

O tempo de resposta da API, medido em condições normais de operação local, deve ter **p95 abaixo de 500 ms**. A medição usa o Locust, com o cenário em [tests/desempenho/locustfile.py](../../tests/desempenho/locustfile.py).

## Cenário

O RNF-10 não define as "condições normais de operação local"; o cenário abaixo foi proposto na issue #113 e registrado na seção 8.1 do guia de desenvolvimento.

| Parâmetro | Valor |
| :--- | :--- |
| Usuários simultâneos | 10, entrando a 5 por segundo |
| Duração | 60 segundos |
| Ambiente | `docker compose up --build`: aplicação e PostgreSQL 16 em containers, em um único Uvicorn |
| Perfil | Gerente, autenticado uma vez por usuário (`POST /auth/login`) |
| Pausa entre ações | de 0,5 a 1,5 s |
| Dados | 30 OS abertas na preparação do teste, cada uma com cliente e veículo próprios |

Rotas medidas, com o peso de cada uma na mistura:

| Rota | Peso |
| :--- | ---: |
| `GET /ordens-servico` (listagem) | 5 |
| `GET /ordens-servico/{id}` (detalhamento) | 3 |
| `GET /ordens-servico?status=RECEBIDA` (listagem filtrada) | 2 |
| `GET /pecas`, `GET /servicos`, `GET /clientes` | 1 cada |
| `POST /ordens-servico` (abertura de OS) | 1 |

As rotas públicas de acompanhamento ficam **fora do cenário**: o limite de 10 requisições por minuto por IP (RNF-05) responderia `429` a quase toda requisição de uma carga vinda de um só endereço. A falha automática é do próprio cenário: ao terminar, se o p95 total passar de 500 ms ou houver qualquer erro, o Locust sai com código 1.

## Resultado

Medição sobre a aplicação do commit `cccdc6d` (`main`, merge do PR #160), em 31/10/2026:

| Métrica | Valor |
| :--- | ---: |
| Requisições | 575 (9,7 por segundo) |
| Erros | 0 |
| Mediana | 34 ms |
| **p95** | **58 ms** |
| p99 | 210 ms |
| Máximo | 240 ms (um login, que calcula o bcrypt) |

A rota mais lenta é a listagem de OS (p95 de 64 ms). O relatório completo está em [desempenho/relatorio-locust.html](desempenho/relatorio-locust.html), e a tabela em [desempenho/locust_stats.csv](desempenho/locust_stats.csv). O p95 ficou 8 vezes abaixo do limite.

## Como reproduzir

Com o `.env` preenchido (`ADMIN_PASSWORD` é a senha do Gerente padrão) e o uv 0.8.22:

```bash
docker compose up --build -d app
uv sync
set -a; . ./.env; set +a
uv run locust -f tests/desempenho/locustfile.py --headless --host http://localhost:8000 \
  --users 10 --spawn-rate 5 --run-time 60s \
  --html docs/evidencias/desempenho/relatorio-locust.html --csv docs/evidencias/desempenho/locust
```

O teste abre OS no banco de desenvolvimento do Compose. Para voltar ao banco limpo, use `docker compose down -v`. Sem `--headless`, o Locust abre a interface em `http://localhost:8089`.

## Quando refazer

A medição muda com o código. Refaça-a sobre o commit final da entrega e atualize a tabela de resultado e o hash do commit.
