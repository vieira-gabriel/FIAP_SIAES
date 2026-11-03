# SIAES - Sistema Integrado de Atendimento e Execução de Serviços

MVP de gestão de uma oficina mecânica, desenvolvido para o Tech Challenge da Fase 1 da pós-graduação SOAT (Software Architecture) da FIAP.

## Objetivo

Organizar o atendimento da oficina do primeiro contato com o cliente até a entrega do veículo. O sistema controla as ordens de serviço (OS), o orçamento, o estoque de peças e o acompanhamento pelo cliente, com regras de negócio explícitas, rastreabilidade de cada mudança de status e segurança no acesso às informações.

## Solução

A aplicação é uma API REST com duas frentes:

| Frente | Quem usa | Acesso | O que oferece |
| :--- | :--- | :--- | :--- |
| **Frente da Loja** | Atendente, Mecânico e Gerente | Autenticado por JWT, com permissões por perfil (RBAC) | Cadastro de clientes, veículos, serviços, peças e usuários; abertura e acompanhamento das OS; diagnóstico, orçamento, execução e entrega; registro no balcão da aprovação ou rejeição dada pelo cliente; relatórios de tempo médio |
| **Frente do Cliente** | Cliente da oficina | Público, identificado pelo número da OS junto com o CPF/CNPJ, com limite de requisições | Consulta do status da OS com a estimativa de entrega; aprovação ou rejeição do orçamento |

O centro do sistema é a **máquina de estados da OS**. Cada transição é feita por um método do agregado `OrdemServico`, que bloqueia as transições inválidas e grava um registro no histórico de status:

```mermaid
stateDiagram-v2
    [*] --> RECEBIDA: Atendente abre a OS
    RECEBIDA --> EM_DIAGNOSTICO: Mecânico assume
    EM_DIAGNOSTICO --> AGUARDANDO_APROVACAO: Orçamento finalizado
    AGUARDANDO_APROVACAO --> AGUARDANDO_EXECUCAO: Cliente aprova, peças reservadas
    AGUARDANDO_APROVACAO --> AGUARDANDO_PECA: Cliente aprova, há peças pendentes
    AGUARDANDO_APROVACAO --> CANCELADA: Cliente rejeita
    AGUARDANDO_PECA --> AGUARDANDO_EXECUCAO: Estoque reposto
    AGUARDANDO_EXECUCAO --> EM_EXECUCAO: Mecânico inicia
    EM_EXECUCAO --> FINALIZADA: Mecânico conclui
    FINALIZADA --> ENTREGUE: Atendente entrega
    ENTREGUE --> [*]
    CANCELADA --> [*]
```

O Gerente também pode cancelar a OS de `RECEBIDA` até `EM_EXECUCAO`, informando o motivo.

Junto com a OS, o sistema cuida de:

- **Orçamento:** soma dos serviços e das peças com os preços congelados no momento do orçamento, para que uma mudança no catálogo não altere uma OS já orçada.
- **Estoque:** reserva das peças na conclusão do orçamento; registro das peças pendentes quando falta saldo; prioridade para a OS mais antiga quando o estoque é reposto; baixa no início da execução e estorno na rejeição ou no cancelamento. O saldo disponível nunca fica negativo.
- **Métricas:** horários de abertura, início da execução e finalização, usados na estimativa de entrega e no relatório de tempo médio de execução.

Os requisitos completos estão em [`docs/requisitos-funcionais.md`](docs/requisitos-funcionais.md) (RF-01 a RF-27) e [`docs/requisitos-nao-funcionais.md`](docs/requisitos-nao-funcionais.md) (RNF-01 a RNF-16).

## Arquitetura

O sistema é um **monólito em camadas** (RNF-01) modelado com **Domain-Driven Design**. O domínio fica isolado em Python puro, sem framework web, ORM nem biblioteca de JWT (RNF-02). As quatro camadas (`domain`, `application`, `infrastructure` e `presentation`) estão descritas em [Estrutura de diretórios](#estrutura-de-diretórios).

- **Regra de dependência:** as dependências apontam sempre para dentro, em direção ao domínio. O domínio não conhece as outras camadas, e os casos de uso dependem de interfaces (portas), não das implementações.
- **Portas e adaptadores:** cada dependência externa (banco, token, hash de senha) é uma interface no domínio ou na aplicação, com a implementação em `infrastructure/`. Só o `presentation/container.py` conhece as implementações e as monta.
- **Agregados:** `OrdemServico`, com os itens, o orçamento e o histórico de status, e `EstoquePeca`, com as quantidades física e reservada de cada peça.
- **Eventos de domínio:** quando a regra de um agregado precisa alterar o outro (por exemplo, a baixa do estoque ao iniciar a execução), o agregado emite um evento, e o Event Dispatcher síncrono chama o handler dentro da mesma transação.
- **Transações:** cada operação crítica roda em uma única unidade de trabalho, com rollback completo em caso de falha (RNF-08).

A arquitetura está documentada nos quatro níveis do [modelo C4](docs/ddd/c4-model.md) (contexto, contêineres, componentes e diagrama de classes). As regras de onde colocar cada parte do código estão no [guia de desenvolvimento](docs/guia-de-desenvolvimento.md).

## Estrutura de diretórios

```text
.
├── src/
│   ├── domain/               Regras de negócio puras (Python puro)
│   │   ├── entities/             Entidades e raízes de agregado
│   │   ├── value_objects/        Objetos de valor imutáveis e enumerações
│   │   ├── events/               Eventos de domínio, um arquivo por evento
│   │   ├── repositories/         Portas (interfaces ABC) de persistência
│   │   └── exceptions.py         Exceções de regra de negócio
│   ├── application/          Orquestração dos casos de uso
│   │   ├── use_cases/            Um arquivo por caso de uso
│   │   ├── ports/                Interfaces de serviços técnicos (token, hash de senha, unidade de trabalho)
│   │   ├── events/               Event Dispatcher síncrono em memória
│   │   └── handlers/             Handlers que reagem aos eventos de domínio
│   ├── infrastructure/       Detalhes técnicos (banco, bibliotecas externas)
│   │   ├── config.py             Leitura e validação das variáveis de ambiente
│   │   ├── database/             Engine, sessão, unidade de trabalho e modelos do SQLAlchemy
│   │   ├── repositories/         Implementações das portas de repositório (PostgreSQL)
│   │   └── security/             Implementações de JWT e hash de senha
│   └── presentation/         Entrada HTTP
│       ├── main.py               Criação do app FastAPI e registro dos routers
│       ├── container.py          Montagem das dependências (único ponto que importa infrastructure)
│       ├── routers/              Rotas FastAPI, um arquivo por recurso
│       ├── schemas/              DTOs de entrada e saída, um arquivo por recurso
│       ├── middlewares/          Validação do token, rate limiting, tratamento de erros e entrega da interface web
│       └── web/                  Páginas da interface web (HTML, CSS e JavaScript)
├── migrations/               Migrations do Alembic
├── tests/
│   ├── unit/                 Testes sem banco e sem HTTP
│   ├── integration/          Testes dos fluxos de ponta a ponta, com PostgreSQL
│   └── desempenho/           Cenário do Locust (RNF-10)
├── docs/
│   ├── ddd/                  Event Storming, Linguagem Ubíqua e modelo C4
│   ├── evidencias/           Cobertura de testes e teste de desempenho
│   └── security/             Análise de vulnerabilidades e revisão de segredos
├── .github/workflows/        Pipeline de CI
├── .env.example              Variáveis de ambiente, sem valores reais
├── Dockerfile                Imagem multi-stage da aplicação
├── docker-compose.yml        Serviços app e db
├── docker-compose.testes.yml Publicação do banco em 127.0.0.1 para os testes de integração
├── alembic.ini               Configuração do Alembic
├── pyproject.toml            Dependências (uv) e configuração do pytest e do Ruff
└── uv.lock                   Versões travadas das dependências
```

O motivo de cada pasta e a regra de dependência entre as camadas estão no [guia de desenvolvimento](docs/guia-de-desenvolvimento.md) e em [`docs/estrutura-de-pastas.md`](docs/estrutura-de-pastas.md).

## Tecnologias

| Área | Tecnologia |
| :--- | :--- |
| Linguagem | Python 3.12 |
| API | FastAPI e Uvicorn, com documentação OpenAPI (Swagger) em `/docs` |
| Banco de dados | PostgreSQL 16 |
| Acesso ao banco | SQLAlchemy 2.0 no modo assíncrono, com o driver asyncpg |
| Migrations | Alembic, aplicado na subida do contêiner |
| Configuração | pydantic-settings, com as variáveis lidas do ambiente (`.env`) |
| Autenticação | JWT com PyJWT e senhas com hash bcrypt |
| Rate limiting | SlowAPI, nas rotas públicas |
| Dependências | uv, com `pyproject.toml` e lockfile `uv.lock` |
| Testes | pytest, pytest-asyncio, pytest-cov e httpx |
| Lint e formatação | Ruff |
| Análise de vulnerabilidades | pip-audit (dependências), Bandit (código) e Trivy (imagem Docker) |
| Teste de desempenho | Locust |
| Execução | Docker (imagem multi-stage) e Docker Compose, com os serviços `app` e `db` |

## Banco de dados

O banco escolhido é o **PostgreSQL 16** (RNF-09), pelos seguintes motivos:

1. **Estrutura relacional forte.** Os dados formam vínculos rígidos: um cliente tem veículos, cada OS pertence a um cliente e a um veículo, e cada OS tem itens de serviço e de peça. O modelo relacional representa essas relações de forma natural.
2. **Integridade referencial.** Chaves estrangeiras e restrições de unicidade (como o documento do cliente e o e-mail do usuário) impedem que uma exclusão ou um dado duplicado corrompa o histórico de atendimentos e o estoque. A exclusão de clientes, veículos, serviços e peças é lógica, para preservar as OS antigas.
3. **Consistência atômica.** A reserva, a baixa e o estorno de peças alteram ao mesmo tempo a OS e o estoque. As transações ACID garantem que essas alterações aconteçam juntas ou não aconteçam (RNF-08), e o controle de concorrência impede que duas OS reservem o mesmo saldo.

O schema é versionado com o Alembic, em `migrations/`, e aplicado automaticamente antes da subida da API.

## Pré-requisitos

| Para | Ferramenta |
| :--- | :--- |
| Executar a aplicação | [Docker](https://docs.docker.com/get-docker/) com o Docker Compose v2 (`docker compose`) |
| Rodar os testes e desenvolver | Os itens acima e o [uv](https://docs.astral.sh/uv/) **0.8.22**, a versão exigida pelo `pyproject.toml`. O uv instala o Python 3.12 sozinho, se ele não estiver na máquina |

Com outra versão do uv instalada, troque para a 0.8.22 com `uv self update 0.8.22` ou use `uvx uv@0.8.22` no lugar de `uv` nos comandos abaixo.

As portas `8000` (API) e, para os testes de integração, `5432` (PostgreSQL) precisam estar livres.

## Como executar

**1. Crie o `.env` a partir do exemplo:**

```bash
cp .env.example .env
```

**2. Preencha as variáveis obrigatórias** no `.env`. A aplicação não inicia se alguma delas estiver vazia (RNF-06):

| Variável | O que informar |
| :--- | :--- |
| `POSTGRES_USER` e `POSTGRES_PASSWORD` | Usuário e senha do banco, criados pelo container `db` na primeira subida |
| `JWT_SECRET_KEY` | Chave de assinatura dos tokens; use um texto aleatório e longo |
| `ADMIN_PASSWORD` | Senha do Gerente padrão, `admin@oficina.com` |
| `SEED_DEMO`, `DEMO_ATENDENTE_PASSWORD` e `DEMO_MECANICO_PASSWORD` | Opcionais: com `SEED_DEMO=true`, as duas senhas passam a ser obrigatórias (veja [Usuários de demonstração](#usuários-de-demonstração)) |

Para gerar uma chave aleatória para o `JWT_SECRET_KEY`, use um dos comandos:

```bash
openssl rand -base64 48
```

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

As demais variáveis já vêm com valores que funcionam no Docker Compose.

**3. Suba a aplicação e o banco:**

```bash
docker compose up --build
```

Na subida, o container `app` aplica as migrations do banco e cria o Gerente padrão (e os usuários e os dados de demonstração, com `SEED_DEMO=true`). A aplicação está pronta quando os dois serviços aparecem como `healthy` em `docker compose ps` e o `http://localhost:8000/health` responde `{"status": "online", "banco": "disponivel", ...}`.

**Para parar:**

```bash
# Mantém os dados do banco para a próxima subida
docker compose down

# Apaga também os dados do banco
docker compose down -v
```

## Interface web

Com a aplicação no ar, a interface fica no próprio endereço da API:

| Endereço | Quem usa | O que oferece |
| :--- | :--- | :--- |
| **http://localhost:8000/oficina/** | Atendente, Mecânico e Gerente, com o mesmo login da API | Quadro das OS por status, abertura da OS com cadastro do cliente e do veículo, diagnóstico e orçamento, aprovação ou rejeição registrada no balcão, execução, entrega, cancelamento, clientes e veículos, serviços, peças e estoque, usuários e relatório de tempos médios. O menu e os botões mudam conforme o perfil |
| **http://localhost:8000/cliente/** | Cliente da oficina, sem login | Consulta da OS pelo número e pelo CPF/CNPJ do titular, com a aprovação ou a rejeição do orçamento |

O detalhe de cada OS traz o link de acompanhamento do cliente (`/cliente/#numero=...`), que já preenche o número da OS. As páginas são HTML, CSS e JavaScript sem etapa de build, em `src/presentation/web/`.

## Swagger e autenticação

A documentação interativa da API (OpenAPI/Swagger) fica em **http://localhost:8000/docs**.

As rotas da Frente da Loja exigem um token JWT. Para usá-las pelo Swagger:

1. Em **Autenticação**, abra `POST /auth/login`, clique em **Try it out** e envie o e-mail e a senha, por exemplo:
   ```json
   {"email": "admin@oficina.com", "senha": "<valor do ADMIN_PASSWORD>"}
   ```
2. Copie o valor de `access_token` da resposta.
3. Clique no botão **Authorize**, no topo da página, cole o token (sem o prefixo `Bearer`) e confirme.
4. As próximas chamadas do Swagger levam o token. Ele vale por 24 horas (`JWT_EXPIRATION_HOURS`).

Sem token, as rotas protegidas respondem `401`; com um perfil sem permissão para a rota, `403`.

## Usuários de demonstração

A carga inicial (RF-03) sempre cria o Gerente padrão. Com `SEED_DEMO=true` no `.env`, cria também um Atendente e um Mecânico, para testar as permissões de cada perfil:

| E-mail | Perfil | Senha | Criado quando |
| :--- | :--- | :--- | :--- |
| `admin@oficina.com` | Gerente | Valor de `ADMIN_PASSWORD` | Sempre |
| `atendente@oficina.com` | Atendente | Valor de `DEMO_ATENDENTE_PASSWORD` | `SEED_DEMO=true` |
| `mecanico@oficina.com` | Mecânico | Valor de `DEMO_MECANICO_PASSWORD` | `SEED_DEMO=true` |

As senhas não têm valor fixo no repositório: cada uma vem do `.env` (RNF-06). Um usuário que já existe não é recriado nem tem a senha trocada quando o container reinicia; para mudar a senha depois da primeira subida, use as rotas de gestão de usuários com o Gerente ou recomece o banco com `docker compose down -v`.

Com `SEED_DEMO=true`, a carga inicial também preenche o banco para a demonstração:

**Serviços**

| Código | Nome | Valor base | Tempo estimado |
| :--- | :--- | ---: | ---: |
| `SRV-OLEO` | Troca de óleo e filtro | R$ 120,00 | 40 min |
| `SRV-FREIO` | Revisão dos freios | R$ 180,00 | 90 min |
| `SRV-ALINHA` | Alinhamento e balanceamento | R$ 150,00 | 60 min |
| `SRV-ELETRICA` | Diagnóstico elétrico | R$ 200,00 | 120 min |
| `SRV-SUSPENSAO` | Troca de amortecedores | R$ 350,00 | 180 min |

**Peças e estoque**, com as quantidades depois das reservas das OS:

| Código | Nome | Preço unitário | Prazo de reposição | Física | Reservada | Saldo disponível |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `FLT-OLEO-01` | Filtro de óleo | R$ 45,00 | 2 dias | 15 | 1 | 14 |
| `PST-FREIO-02` | Pastilha de freio dianteira | R$ 160,00 | 3 dias | 6 | 2 | 4 |
| `AMT-DIANT-03` | Amortecedor dianteiro | R$ 420,00 | 7 dias | 0 | 0 | 0 |

**Clientes e veículos**

| Cliente | CPF/CNPJ | E-mail | Telefone | Veículo |
| :--- | :--- | :--- | :--- | :--- |
| Ana Souza | 529.982.247-25 | `ana.souza@exemplo.com` | 11912345678 | `ABC1D23`, Volkswagen Gol 2018 |
| Bruno Lima | 111.444.777-35 | `bruno.lima@exemplo.com` | 11923456789 | `BRA2E19`, Fiat Argo 2021 |
| Carla Mendes | 390.533.447-05 | `carla@exemplo.com` | 21934567890 | `CDE3F45`, Chevrolet Onix 2020 |
| Daniel Rocha | 987.654.321-00 | `daniel@exemplo.com` | 31945678901 | `DEF4567`, Toyota Corolla 2016 |
| Transportes Rápidos Ltda | 11.222.333/0001-81 | `frota@exemplo.com` | 1134567890 | `FRT5G67`, Mercedes-Benz Sprinter 2022 |

**Ordens de serviço**, da mais antiga para a mais nova. A abertura é contada a partir da subida da aplicação; o Atendente e o Mecânico de demonstração aparecem no histórico.

| Abertura | Status | Cliente e veículo | Serviços | Peças | Total |
| :--- | :--- | :--- | :--- | :--- | ---: |
| 40 dias antes | `ENTREGUE` | Daniel Rocha, `DEF4567` | Alinhamento e balanceamento | — | R$ 150,00 |
| 20 dias antes | `ENTREGUE`, depois de 67 h em `AGUARDANDO_PECA` | Transportes Rápidos, `FRT5G67` | Troca de amortecedores, alinhamento e balanceamento | 2 amortecedores (baixados) | R$ 1.340,00 |
| 6 dias antes | `FINALIZADA` | Ana Souza, `ABC1D23` | Troca de óleo e filtro | 1 filtro de óleo (baixado) | R$ 165,00 |
| 4 dias antes | `CANCELADA` (orçamento rejeitado pelo cliente) | Carla Mendes, `CDE3F45` | Diagnóstico elétrico | — | R$ 200,00 |
| 3 dias antes | `EM_EXECUCAO` | Bruno Lima, `BRA2E19` | Revisão dos freios | 1 pastilha (baixada) | R$ 340,00 |
| 2 dias antes | `AGUARDANDO_PECA` | Daniel Rocha, `DEF4567` | Troca de amortecedores | 2 amortecedores (pendentes) | R$ 1.190,00 |
| 40 horas antes | `AGUARDANDO_EXECUCAO` | Transportes Rápidos, `FRT5G67` | Revisão dos freios, troca de óleo e filtro | 1 pastilha e 1 filtro de óleo (reservados) | R$ 505,00 |
| 26 horas antes | `AGUARDANDO_APROVACAO` | Ana Souza, `ABC1D23` | Revisão dos freios | 1 pastilha (reservada) | R$ 340,00 |
| 5 horas antes | `EM_DIAGNOSTICO` | Carla Mendes, `CDE3F45` | Troca de óleo e filtro | 1 filtro de óleo (sem reserva até o orçamento) | — |
| 1 hora antes | `RECEBIDA` | Bruno Lima, `BRA2E19` | — | — | — |

As duas OS entregues são finalizadas com 22 dias de diferença, e uma delas esperou peça, para o relatório de tempos médios ter o que mostrar. As reservas das peças seguem o estoque. Serviço e peça já cadastrados com o mesmo código são mantidos, e as OS só são criadas se o banco não tiver nenhuma; para recriá-las, recomece o banco com `docker compose down -v`.

## Testes

Os testes ficam em `tests/unit/` (domínio e casos de uso, sem banco) e `tests/integration/` (rotas HTTP e repositórios, com PostgreSQL). Antes da primeira execução, instale as dependências:

```bash
uv sync
```

**Testes unitários**, sem banco:

```bash
uv run pytest tests/unit
```

**Testes de integração**, com o `.env` preenchido como na seção [Como executar](#como-executar). Eles usam um banco separado, `<POSTGRES_DB>_test`, recriado a cada execução, sem tocar nos dados da aplicação:

```bash
docker compose -f docker-compose.yml -f docker-compose.testes.yml up -d db
uv run pytest tests/integration
```

Sem o banco no ar, os testes de integração são pulados, e `uv run pytest` roda só os unitários.

**Todos os testes, com a cobertura** do domínio e da aplicação (RNF-14, mínimo de 80%):

```bash
uv run pytest --cov --cov-report=term-missing --cov-fail-under=80
```

A medição salva (100% em `domain/` e em `application/`) está em [`docs/evidencias/cobertura.md`](docs/evidencias/cobertura.md).

**Lint e formatação:**

```bash
uv run ruff check src tests migrations
uv run ruff format --check src tests migrations
```

O CI (`.github/workflows/ci.yml`) roda tudo isso em cada Pull Request, com um PostgreSQL 16, e também o Bandit e o pip-audit (RNF-07).

## Desempenho

O tempo de resposta (RNF-10, p95 abaixo de 500 ms) é medido com o Locust, contra a aplicação no ar. Com o `.env` preenchido, `docker compose up --build -d app` e `uv sync` feitos:

```bash
set -a; . ./.env; set +a
uv run locust -f tests/desempenho/locustfile.py --headless --host http://localhost:8000 --users 10 --spawn-rate 5 --run-time 60s
```

O comando sai com código 1 se o p95 passar de 500 ms ou houver erro. O cenário, o resultado (p95 de 62 ms) e o relatório do Locust estão em [`docs/evidencias/desempenho.md`](docs/evidencias/desempenho.md).

## Documentação

- [Requisitos funcionais](docs/requisitos-funcionais.md) e [não funcionais](docs/requisitos-nao-funcionais.md)
- [Event Storming (board no Miro e PDF)](docs/ddd/event-storming.md)
- [Linguagem ubíqua](docs/ddd/linguagem-ubiqua.md)
- [Modelo C4](docs/ddd/c4-model.md)
- [Guia de desenvolvimento](docs/guia-de-desenvolvimento.md)
- Evidências de qualidade: [cobertura de testes](docs/evidencias/cobertura.md) e [desempenho](docs/evidencias/desempenho.md)
- Segurança: [análise de vulnerabilidades](docs/security/analise-de-vulnerabilidades.md) e [revisão de segredos](docs/security/revisao-de-segredos.md)
