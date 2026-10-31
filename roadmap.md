# Roadmap de Desenvolvimento - MVP SIAES

Este documento organiza o desenvolvimento do MVP do **Sistema Integrado de Atendimento e Execução de Serviços (SIAES)** em fases, da fundação do projeto até a entrega final do Tech Challenge da Fase 1. Cada tarefa referencia os requisitos de [requisitos-funcionais.md](docs/requisitos-funcionais.md) (RF) e [requisitos-nao-funcionais.md](docs/requisitos-nao-funcionais.md) (RNF), o [modelo C4](docs/ddd/c4-model.md) e os itens exigidos pelo enunciado. Para saber onde e como implementar cada tarefa, siga o [guia de desenvolvimento](docs/guia-de-desenvolvimento.md).

**Como usar:** marque a tarefa como concluída (`[x]`) no mesmo Pull Request que a entrega. A ordem das fases segue as dependências técnicas; fases sem dependência entre si podem andar em paralelo.

---

## Estado Atual

> Atualizado em 29/10/2026, considerando a `main` até o merge do PR #134 e a issue #45.

| Item | Situação |
| :--- | :--- |
| Requisitos funcionais e não funcionais | Revisados no fechamento da Fase 0 (RF-01 a RF-27, RNF-01 a RNF-16), com peça pendente, fila de execução, histórico de status, listagem e detalhamento de OS e os RNFs exigidos pelo enunciado restaurados |
| Linguagem ubíqua | Atualizada com os 9 status, a tabela de transições e os termos de estoque; os nomes ainda divergem do modelo C4 em alguns pontos (Fase 1) |
| Modelo C4 | Documentado nos 4 níveis; camada de entrada renomeada para `src/presentation/`; estrutura de pastas da seção 6 aprovada pelo grupo (issue #9) |
| Guia de desenvolvimento e estrutura de pastas | Atualizados para a numeração atual dos requisitos, com as decisões técnicas da seção 8 |
| Event Storming | PDF reexportado com os fluxos de peça pendente e de cancelamento; link do board registrado em [docs/ddd/event-storming.md](docs/ddd/event-storming.md) |
| Código (`src/`) e testes | Domínio implementado: objetos de valor, `Cliente`, `Veiculo`, `Usuario`, `Servico`, `Peca`, `OrdemServico` (itens, orçamento, máquina de estados, histórico e estimativa de entrega) e `EstoquePeca` (reserva, baixa, estorno e alocação por prioridade), com os quatro eventos de domínio acumulados por eles e as sete portas de repositório (cliente, veículo, usuário, serviço, peça, estoque e OS). Aplicação com o Event Dispatcher e os casos de uso de login, de carga inicial e dos cadastros de usuários (issue #81), clientes (issue #82), veículos (issue #83), serviços (issue #84) e peças com o saldo do estoque (issue #85). Infraestrutura com configuração, engine, unidade de trabalho, seis migrations (`usuarios`, `clientes`, `servicos`, `veiculos`, `pecas` e `estoque_pecas`) e a persistência desses cadastros. Apresentação com `/health`, login, validação de token com checagem de perfil (RBAC), rotas `/usuarios`, `/clientes`, `/veiculos`, `/servicos` e `/pecas`, as rotas de OS (abertura, detalhamento, listagem, atribuição do mecânico, itens e conclusão do orçamento) e tratamento padronizado de erros. 1606 testes passando (1121 unitários e 485 de integração), com 100% de cobertura em `domain/` e `application/` |
| Configuração do repositório | `.gitignore`, `.env.example`, `pyproject.toml` (com o uv fixado em 0.8.22) e `uv.lock` criados. A proteção da `main` no GitHub ainda não está configurada (API: `protected: false`, sem ruleset) |
| CI | `.github/workflows/ci.yml` em cada PR e em cada push na `main`: lint, testes com PostgreSQL, cobertura mínima de 80%, Bandit, pip-audit e `docker build` (issue #29) |
| Docker | `Dockerfile` em Python 3.12, multi-stage com `uv`, usuário não-root e sem o `pip` da imagem base, e `docker-compose.yml` com `app` e `db` (PostgreSQL 16); as migrations rodam antes do Uvicorn |
| Segurança | Revisão de segredos no código e no histórico (issue #114, `docs/security/revisao-de-segredos.md`) e análise de vulnerabilidades das dependências, do código e da imagem (issue #111, `docs/security/analise-de-vulnerabilidades.md`), ambas sem achado crítico e a repetir no commit final. Medição de desempenho, revisão de SQL Injection, IDOR e XSS e revisão do Swagger seguem pendentes (Fase 7) |
| Pendências do domínio | Nenhuma regra de domínio: `OrdemServico.alocar_peca` (issue #43) e os eventos de domínio (issue #45) estão prontos. A persistência da OS (issue #88), a abertura da OS (issue #90) e a conclusão do orçamento, com o despacho do evento na transação (issues #89 e #92), estão prontas. O `ReservaPecasHandler` (issue #93) e o `AlocacaoPecasPendentesHandler` (issue #94) já estão registrados em `app.state.fabricas_de_handlers`; os handlers do estorno e da baixa entram com a Fase 5 |
| README | Objetivo, solução, arquitetura, tecnologias e banco de dados (issue #116), pré-requisitos, execução, testes, Swagger e usuários de demonstração (issue #117); faltam a estrutura de diretórios, o link para a documentação DDD e o link do vídeo (issue #121) |

---

## Visão Geral das Fases

```mermaid
flowchart LR
  F0["Fase 0<br/>Fundação"] --> F1["Fase 1<br/>Modelagem DDD"]
  F0 --> F2["Fase 2<br/>Infraestrutura base"]
  F1 --> F3["Fase 3<br/>Domínio"]
  F2 --> F4["Fase 4<br/>Autenticação e cadastros"]
  F3 --> F4
  F4 --> F5["Fase 5<br/>Fluxo da OS"]
  F5 --> F6["Fase 6<br/>Gestão e métricas"]
  F6 --> F7["Fase 7<br/>Qualidade e segurança"]
  F7 --> F8["Fase 8<br/>Documentação e entrega"]
```

| Fase | Objetivo | Depende de | Resultado esperado | Situação |
| :--- | :--- | :--- | :--- | :--- |
| **0** | Fundação | - | Decisões fechadas, documentos alinhados entre si e ao enunciado, repositório configurado | Em andamento |
| **1** | Modelagem DDD | 0 | Event Storming completo e legível, diagramas e linguagem ubíqua consistentes entre si | Em andamento |
| **2** | Infraestrutura base | 0 | `docker compose up --build` sobe API + PostgreSQL com Swagger em `/docs` | Concluída |
| **3** | Domínio | 1 | Entidades, objetos de valor, eventos e regras de negócio com testes unitários | Concluída |
| **4** | Autenticação e cadastros | 2, 3 | Login JWT, RBAC, gestão de usuários e cadastros administrativos | Concluída (login, RBAC, carga inicial, usuários, clientes, veículos, serviços e peças) |
| **5** | Fluxo da OS | 4 | Abertura, orçamento, reserva e pendência de peças, aprovação, execução e consulta pública | Não iniciada |
| **6** | Gestão e métricas | 5 | Listagem, detalhamento e relatório de tempos médios | Não iniciada |
| **7** | Qualidade e segurança | 6 | Cobertura ≥ 80% comprovada, relatório de vulnerabilidades e medição de desempenho | Não iniciada |
| **8** | Documentação e entrega | 7 | README, documentação DDD final, vídeo e PDF de entrega | Em andamento (README sem a estrutura de diretórios e os links da documentação DDD e do vídeo) |

---

## Fase 0 - Fundação

**Objetivo:** fechar as decisões que bloqueiam o restante do trabalho, alinhar os documentos entre si e ao enunciado e preparar o repositório.

### Pendências do Merge da Branch `docs/fechamento-fase-0`

A branch `docs/fechamento-fase-0` entrou na `main` pelo PR #20, junto com o health check do commit `c63c963`. Ficaram pendentes:

- [x] Fazer o merge da branch na `main` por Pull Request (PR #20)
- [x] Decidir onde fica a aplicação FastAPI e como as dependências são instaladas no Docker: a aplicação está em `src/presentation/main.py`, com as rotas em `presentation/routers/`, e o Docker instala as dependências com `uv sync` a partir do `pyproject.toml` e do `uv.lock`

### Decisões Técnicas

As decisões estão registradas na seção 8 do [guia de desenvolvimento](docs/guia-de-desenvolvimento.md), com os custos das opções em aberto.

| Decisão | Definição | Onde está registrada |
| :--- | :--- | :--- |
| Linguagem | Python 3.12 | RNF-02 |
| Framework web | FastAPI + Uvicorn | Modelo C4, guia §8.1 |
| Banco de dados | PostgreSQL 16 | RNF-09 |
| ORM | SQLAlchemy 2.0 | RNF-04, guia §8.1 |
| JWT e hash de senha | PyJWT e bcrypt | RF-01, RF-03, guia §8.1 |
| Testes e cobertura | pytest + pytest-cov | RNF-12 a RNF-14 |
| Eventos de domínio | Event Dispatcher síncrono em memória | Modelo C4 |
| Módulos críticos (meta de 80%) | Domínio e aplicação | RNF-14 |
| Documentação da API | Swagger UI em `/docs` | RNF-16 |
| Branches e commits | Branches `<tipo>/<descricao-curta>` e commits `<tipo>: <descrição>` em português | Guia §7 |
| Imports | Absolutos a partir de `src/`, com `PYTHONPATH=src` | Guia §4.2 e §8.1 |
| Arquivo de dependências | `pyproject.toml` com `uv` e `uv.lock` | Guia §8.1 |
| Lint e formatação | Ruff | Guia §8.1 |
| Rate limiting | SlowAPI com contador em memória | RNF-05 |
| Rotas e DTOs | `presentation/routers/` e `presentation/schemas/`, um arquivo por recurso | Guia §3 e §8.1 |
| CI | Opcional, somente se houver tempo | Guia §8.1 |
| Modo do SQLAlchemy | Assíncrono com asyncpg e pytest-asyncio (issue #3) | Guia §8.1 |
| Migrations | Alembic com o template `async`, pasta `migrations/` na raiz (issue #4) | Guia §8.1 |
| Análise de vulnerabilidades | pip-audit, Bandit e Trivy, sem Dependabot (issue #5) | RNF-07, guia §8.1 |
| Teste de desempenho | Locust (issue #6); cenário de medição pendente | RNF-10, guia §8.1 e §8.2 |

### Decisões de Domínio

- [x] Transições de status e responsáveis por cada uma ([linguagem-ubiqua.md](docs/ddd/linguagem-ubiqua.md) seção 5)
- [x] Identificação do cliente na consulta pública: número da OS + CPF/CNPJ (RF-25)
- [x] Aprovação e rejeição do orçamento pelo cliente em rota pública (RF-26)
- [x] Perfis de acesso com RBAC: Atendente, Mecânico e Gerente (RF-02)
- [x] Carga inicial do usuário Gerente `admin@oficina.com` (RF-03)
- [x] Remoção lógica de clientes e veículos (RF-06, RF-09)
- [x] Exclusão de serviços e peças: lógica (RF-11, RF-12)
- [x] Saldo insuficiente na conclusão do orçamento: reserva parcial, peças pendentes, novo status `AGUARDANDO_PECA` após a aprovação e alocação automática na reposição, com prioridade para a OS de abertura mais antiga (RF-18, RF-19, RF-26)
- [x] Novo status `AGUARDANDO_EXECUCAO`: a aprovação leva à fila de execução, e o mecânico atribuído ou o Gerente inicia a execução, quando ocorre a baixa das peças (RF-20)
- [x] Estimativa de entrega: tempo estimado por serviço e prazo de reposição das peças pendentes, sempre exibida como data (RF-11, RF-12, RF-25)
- [x] Tempo de espera por peça contabilizado na estimativa de entrega, em métrica própria e no tempo total da OS (RF-25, RF-27)
- [x] Histórico de status com toda transição: status anterior, novo status, data/hora, origem, usuário e motivo (RF-24)
- [x] Cancelamento exclusivo do Gerente, de `RECEBIDA` até `EM_EXECUCAO`, com motivo; reservas estornadas e peças baixadas consideradas consumidas; sem alteração arbitrária de status (RF-23)
- [x] Sem remoção de OS: o cancelamento substitui o comando "Remover OS" do Event Storming
- [x] Atualização de saldo por Mecânico e Gerente; dados cadastrais da peça alterados só pelo Gerente; Atendente apenas consulta peças (RF-12)
- [x] Número da OS: 3 primeiros dígitos do CPF/CNPJ + 8 caracteres do UUID interno (RF-13)
- [x] Usuários de demonstração de Atendente e Mecânico criados quando `SEED_DEMO=true` (RF-03)
- [x] Senha do usuário da carga inicial lida de `ADMIN_PASSWORD`, obrigatória e sem valor padrão (RF-03, RNF-06)
- [x] Registrar na documentação os status acrescentados ao enunciado (`AGUARDANDO_PECA`, `AGUARDANDO_EXECUCAO`, `CANCELADA`) e o motivo (seção 5 dos RFs)

### Alinhamento dos Requisitos com o Enunciado

- [x] **Gestão de segredos:** RNF-06
- [x] **Análise de vulnerabilidades:** RNF-07
- [x] **Testes de integração dos fluxos principais:** RNF-13
- [x] **Listagem e detalhamento de Ordens de Serviço:** RF-14 e RF-15, com filtros por status, mecânico, cliente ou placa e período
- [x] **Descontos e taxas:** menção removida do RNF-12
- [x] **Identificação na consulta pública:** número da OS + CPF/CNPJ em RF-25, RF-26, RNF-04 e no modelo C4

### Atualização do Guia de Desenvolvimento e da Estrutura de Pastas

- [x] Atualizar a numeração dos requisitos citados
- [x] Seção 5.6 do guia: incluir a aprovação e a rejeição do orçamento entre as rotas públicas e restringir a identificação a número da OS + CPF/CNPJ
- [x] Guia e estrutura de pastas: usar o perfil `Gerente` e prever a resposta `403`
- [x] Seção 5.4 do guia: regras atuais de estoque (reserva, pendência, baixa no início da execução e estorno)
- [x] Seção 5.2 do guia: timestamps de abertura, início e fim da execução e histórico de status
- [x] Seção 8 do guia: decisões tomadas e decisões em aberto, com os custos das opções
- [x] Revisar as citações a RNFs removidos ou renumerados

### Repositório

- [ ] Proteger a branch `main` no GitHub (Settings → Branches): exigir PR com 1 aprovação, bloquear push forçado e marcar o check "Lint, testes e segurança" do CI como obrigatório. O enunciado exige a proteção. Em 28/10/2026 a API do GitHub devolvia `protected: false` e nenhum ruleset, com o repositório público; a configuração depende do dono do repositório
- [x] Definir o padrão de branches e de mensagens de commit (guia de desenvolvimento, seção 7)
- [x] Criar `.gitignore` para Python (incluindo `.env`, `.venv/`, `__pycache__/`, relatórios de cobertura e o PDF do enunciado)
- [x] Remover da `main` os arquivos `.pyc` commitados no health check; o `.gitignore` ignora `__pycache__/`
- [x] Criar `.env.example` com as variáveis necessárias, sem valores reais
- [x] Unificar o arquivo de dependências: só o `pyproject.toml` (com o `uv.lock`) permanece, conforme a seção 8.1 do guia; o `requirements.txt` foi removido
- [x] Gerar o `uv.lock` com `uv lock` após a decisão do driver do PostgreSQL e da ferramenta de migrations (issue #8)

### Estrutura de Pastas

- [x] Reorganizar os arquivos de código em camadas (`domain`, `application`, `infrastructure`, `presentation`) (PR #1)
- [x] Separar `tests/unit/` e `tests/integration/` e criar `docs/security/` (PR #1)
- [x] Criar `presentation/routers/` e transformar `presentation/schemas.py` em pasta
- [x] Unificar a estrutura de pastas com a seção 6 do modelo C4 (issue #9)
- [x] Atualizar as seções 1 e 4 do modelo C4 para `src/presentation/`

| Pasta | Modelo C4 (seção 6) | Código e guia |
| :--- | :--- | :--- |
| `presentation/routers/` | Prevista | Criada |
| `presentation/schemas/` | Prevista | Criada |
| `presentation/middlewares/` | Prevista (JWT e rate limiting) | Criada; substitui `presentation/auth/` |
| `application/events/` e `application/handlers/` | Previstas (Event Dispatcher e `BaixaEstoqueHandler`) | Criadas |
| `domain/events/` | Prevista (eventos de domínio) | Criada |
| `infrastructure/database/` | Prevista (engine e sessões do SQLAlchemy) | Criada; inclui também os modelos do ORM |

---

## Fase 1 - Modelagem DDD

**Objetivo:** concluir uma modelagem legível e consistente entre todos os documentos. Os nomes definidos aqui são os que aparecerão nas classes, e o enunciado não aceita documentação que não corresponda à implementação.

### Event Storming

- [x] Event Storming do fluxo de criação da OS (área "Criação da ordem de serviço")
- [x] Event Storming do acompanhamento da OS (área "Acompanhar OS")
- [x] Fluxo de peça pendente, reposição de estoque e cancelamento pelo Gerente no board
- [x] Event Storming da gestão administrativa (área "Gestão administrativa"): CRUD de serviços, peças, clientes, veículos e OSs com validação de perfil
- [x] Confirmar que a área "Gestão administrativa" cobre a gestão de peças e insumos, exigida explicitamente pelo enunciado
- [x] Reexportar [event-storming.pdf](docs/ddd/event-storming.pdf) com o texto dos post-its legível com zoom de 100%
- [x] Garantir acesso público ao board (Miro ou equivalente), sem necessidade de pedir permissão, e registrar o link no repositório ([docs/ddd/event-storming.md](docs/ddd/event-storming.md))
- [x] Transcrever em texto os eventos de domínio, comandos, políticas e atores levantados, para referência no código e na linguagem ubíqua ([docs/ddd/event-storming.md](docs/ddd/event-storming.md))
- [x] Completar o board com o estorno no cancelamento, a aprovação do orçamento em uma única área e um título que identifique o projeto (seção 6 de [docs/ddd/event-storming.md](docs/ddd/event-storming.md)); a aprovação em uma única área e o título foram descartados pelo grupo (motivo nos comentários da issue #49)

**Lacunas do quadro atual do Event Storming** (levantadas em 15/10/2026 com base nas imagens exportadas do Miro; a seção 6 de [docs/ddd/event-storming.md](docs/ddd/event-storming.md) registra como cada divergência é tratada):

- [ ] Modelar as etapas finais da OS, hoje reduzidas ao comando genérico "Atualizar status da OS": execução iniciada, manutenção concluída (mecânico) e veículo entregue (atendente), com os timestamps usados no tempo médio de execução. Execução iniciada e manutenção concluída entram na área "Ciclo de vida da OS aprovada" (issue #19); falta o veículo entregue
- [ ] Modelar a baixa do estoque no início da execução e o estorno no cancelamento; a reserva após o orçamento gerado e o estorno na reprovação já constam no board. O estorno no cancelamento entrou com a issue #49, e a baixa entra na área "Ciclo de vida da OS aprovada" (issue #19)
- [x] Gestão de peças e insumos: o board separa cadastro, atualização de dados e atualização de saldo da peça e liga o saldo atualizado à liberação das OS com peça pendente; o algoritmo de alocação do RF-19 é representado no board, na área "Ciclo de vida da OS aprovada"
- [ ] Incluir os fluxos que os requisitos citam e o quadro não mostra: gestão de usuários internos pelo Gerente e relatório de tempo médio de execução
- [ ] Incluir os caminhos de erro: credenciais inválidas na consulta pública, estoque insuficiente e transição de status inválida
- [ ] Representar os demais elementos de DDD exigidos pelo enunciado: o agregado `EstoquePeca` (hoje só aparece `Ordem de Serviço`), entidades, objetos de valor e bounded contexts
- [ ] Revisar detalhes: nomear a credencial do cliente como CPF/CNPJ, como nos requisitos; conferir a legenda "PA" (losango vermelho). Já resolvidos: "Entra com credenciais", política de perfil em "Atualizar saldo da peça" (Gerente e Mecânico, RF-12) e a seta da área de criação da OS, que liga ao "Criar OS" da administração

### Consistência entre Documentos

- [x] Padronizar os objetos de valor de documento: `CPF` e `CNPJ` em classes separadas (`cpf.py` e `cnpj.py`), como na linguagem ubíqua; modelo C4 e estrutura de pastas atualizados (issue #14)
- [x] Incluir na linguagem ubíqua os termos ainda ausentes do modelo C4: `Usuario`, `PerfilUsuario`, `ItemServico`, `ItemPeca` e eventos de domínio ([docs/ddd/linguagem-ubiqua.md](docs/ddd/linguagem-ubiqua.md), seções 1, 2 e 7)
- [x] Usar o objeto de valor `Valor` (precisão decimal) nos preços do diagrama de classes, que hoje aparecem como `float` (seção 5 de [docs/ddd/c4-model.md](docs/ddd/c4-model.md))
- [x] Completar o diagrama de classes com `Servico` (tempo estimado), `Peca`/`EstoquePeca` (quantidade reservada e prazo de reposição), `Orcamento` e `HistoricoStatusOS`, e esclarecer se `Peca` e `EstoquePeca` são a mesma entidade (são entidades separadas, na relação 1:1; decisão registrada na seção 5 de [docs/ddd/c4-model.md](docs/ddd/c4-model.md))
- [x] Listar todos os eventos de domínio; o modelo C4 cita `OrcamentoAprovadoEvent`, `ExecucaoIniciadaEvent` e `StatusOSAlteradoEvent`, mas reserva, estorno, reposição de estoque e liberação de OS também dependem de eventos (seção 7 de [docs/ddd/event-storming.md](docs/ddd/event-storming.md); `OrcamentoAprovadoEvent` e `StatusOSAlteradoEvent` deixaram de ser classes porque nenhum outro agregado os consome)

### Diagramas

- [x] Modelo C4 nos níveis de contexto, contêineres, componentes e código
- [x] Bounded contexts e máquina de estados descritos na linguagem ubíqua
- [x] Conferir no material da disciplina de DDD quais diagramas são obrigatórios e produzir os que faltarem: os professores confirmaram que são o Event Storming ([docs/ddd/event-storming.md](docs/ddd/event-storming.md)) e o modelo C4 ([docs/ddd/c4-model.md](docs/ddd/c4-model.md)), e nenhum faltava
- [ ] ~~Exportar os diagramas para `docs/ddd/diagramas.pdf`, estrutura sugerida pelo enunciado~~ **Descartado**: os diagramas exigidos são só o Event Storming e o C4, que já têm documento próprio (motivo nos comentários da issue #19)
- [ ] Completar o Event Storming com o ciclo de vida da OS da aprovação até a finalização (área "Ciclo de vida da OS aprovada", issue #19)

---

## Fase 2 - Infraestrutura Base

**Objetivo:** ter o ambiente completo subindo com um único comando antes de iniciar as funcionalidades.

**Já feito (commit `c63c963`, Guilherme):** rota `GET /health`, `Dockerfile` e `docker-compose.yml` com o serviço `api` e healthcheck. Ajustes feitos nessa primeira versão:

- [x] `Dockerfile`: Python 3.12, build multi-stage com `uv` e execução com usuário não-root (RNF-15)
- [x] `Dockerfile`: o comando passou a `uvicorn presentation.main:app`, sem o prefixo `src.`, com `PYTHONPATH=/app/src`
- [x] `docker-compose.yml`: sem o volume `.:/app` e sem o campo `version`
- [x] `src/presentation/api/` deixou de existir: a aplicação está em `presentation/main.py` e as rotas em `presentation/routers/`

Tarefas da fase:

- [x] `docker-compose.yml` com os serviços `app` e `db` (PostgreSQL 16), volume persistente para o banco e healthcheck, subindo com `docker compose up --build` (RNF-15)
- [x] Configuração do `PYTHONPATH` para os imports a partir de `src/` funcionarem localmente, no Docker e no pytest
- [x] Configuração por variáveis de ambiente, sem segredos no código e com falha na inicialização quando faltar variável obrigatória (RNF-06; `infrastructure/config.py`)
- [x] Engine e sessão do SQLAlchemy com controle de transação e rollback completo em caso de falha (RNF-08; issue #24)
- [x] Migrations iniciais com Alembic (`alembic init -t async migrations`, seção 8.1 do guia; issue #25): revisão de base vazia aplicada antes do Uvicorn; as tabelas entram com cada entidade
- [x] Rota de health check na aplicação FastAPI (`GET /health`), agora consultando o banco: `200` com o banco disponível e `503` sem ele (issue #26)
- [x] Swagger em `/docs` com título, versão, descrição e o esquema Bearer JWT (botão "Authorize") (RNF-16; issue #26)
- [x] Ligar o login à aplicação: `obter_autenticar_usuario` no container e registro do router de autenticação, com o repositório de usuários em PostgreSQL (modelo do ORM, migration `0002` e adaptador)
- [x] Tratamento padronizado de erros, traduzindo as exceções do domínio para códigos HTTP, incluindo `401` e `403` (RNF-03; issue #30): corpo único `ErroResponse` e tabela na seção 5.5 do guia
- [x] Event Dispatcher síncrono em memória (Modelo C4; `application/events/event_dispatcher.py`)
- [x] Estrutura para testes de integração com banco PostgreSQL de teste (RNF-13; issue #28): banco `<POSTGRES_DB>_test` no container `db`, fixtures em `tests/integration/conftest.py` e comandos na seção 5.7 do guia
- [x] (Opcional, se houver tempo) Pipeline de CI no GitHub Actions executando lint, testes e cobertura em cada Pull Request (issue #29), com Bandit e pip-audit (RNF-07)

---

## Fase 3 - Domínio

**Objetivo:** implementar o núcleo de regras de negócio com `dataclasses` puras, sem dependência de framework ou ORM (RNF-02). É a camada que concentra a meta de cobertura. As receitas de objeto de valor, entidade e porta de repositório estão nas seções 5.1 a 5.3 do guia.

**Dependência da Fase 1:** as etapas finais da OS, o estorno de estoque e o agregado `EstoquePeca` precisam estar modelados antes da implementação (ver lacunas do Event Storming).

### Objetos de Valor

- [x] CPF e CNPJ com validação dos dígitos verificadores (RF-05)
- [x] `Placa` nos padrões antigo (`ABC1234`) e Mercosul (`ABC1D23`) (RF-08)
- [x] `Valor` com precisão decimal
- [x] `NumeroOS` no formato `DDD-XXXXXXXX` (RF-13)
- [x] `StatusOS`, `PerfilUsuario` e `OrigemTransicao`

### Entidades e Agregados

- [x] Exceções de regra de negócio em `src/domain/exceptions.py`
- [x] `Cliente`, `Veiculo`, `Usuario`, `Servico` (com tempo estimado) e `Peca` (com prazo de reposição), com exclusão lógica (RF-06, RF-09, RF-11, RF-12)
- [x] Agregado `OrdemServico` com `ItemServico` e `ItemPeca`, congelando os preços vigentes na conclusão do orçamento (RF-13, RF-17, RNF-11; issue #39): itens só em `EM_DIAGNOSTICO`, apenas ativos e sem repetição, e `congelar_valores` atualiza os itens com os valores vigentes do catálogo
- [x] Cálculo do orçamento como soma dos valores congelados (RF-17; issue #39): objeto de valor `Orcamento` com os subtotais de serviços e de peças e o total
- [x] Máquina de estados com os 9 status e bloqueio de transições inválidas: `atribuir_mecanico`, `finalizar_orcamento`, `aprovar_orcamento`, `rejeitar_orcamento`, `liberar_para_execucao`, `iniciar_execucao`, `concluir_manutencao`, `entregar_veiculo` e `cancelar` (linguagem ubíqua §5; issue #40): cada método declara de quais status parte, e o histórico (#41) e os eventos (#45) se encaixam no `_mudar_status`
- [x] Registro dos timestamps de abertura, início da execução e finalização (RF-13, RF-20, RF-21; issue #40)
- [x] Bloqueio de alteração de itens após `FINALIZADA` (RF-21; issue #40): os itens só mudam em `EM_DIAGNOSTICO`
- [x] Histórico de status com origem, usuário e motivo obrigatório no cancelamento (RF-24, RF-23; issue #41): `HistoricoStatusOS` imutável, histórico da OS somente leitura, registro de abertura criado por `OrdemServico.abrir` e um registro por transição, gravado pelo `_mudar_status`
- [x] Agregado `EstoquePeca` com quantidade física, reserva, pendência, baixa e estorno, sem permitir saldo negativo (RF-12, RF-18, RF-20; issue #42): `reservar` devolve (reservada, pendente), `SaldoPecaAtualizadoEvent` acumulado quando o saldo aumenta, e porta `EstoqueRepository`; a alocação por prioridade (`alocar_pendencias`) fica na #43
- [x] Regra de prioridade pela OS mais antiga na reserva e na alocação de peças repostas (RF-18, RF-19; issue #43): `PendenciaPeca`, `AlocacaoPeca` e `EstoquePeca.alocar_pendencias` (parte 1) e `OrdemServico.alocar_peca`, que converte a quantidade pendente do item em reservada e libera a OS de `AGUARDANDO_PECA` para `AGUARDANDO_EXECUCAO` quando não resta pendência (parte 2)
- [x] Cálculo da estimativa de entrega por status (RF-25; issue #44): `OrdemServico.estimar_entrega(momento_consulta)` com os valores congelados nos itens e uma linha de teste para cada status da tabela
- [x] Eventos de domínio acumulados nos agregados (`collect_domain_events`; issue #45): `DomainEvent` e os quatro eventos do catálogo (`OrcamentoFinalizadoEvent`, `OSCanceladaEvent`, `ExecucaoIniciadaEvent` e `SaldoPecaAtualizadoEvent`), acumulados pela `OrdemServico` e pelo `EstoquePeca`, e o objeto de valor `QuantidadePeca` das listas de estornos e de baixas. A unificação da validação da quantidade de peça segue em aberto (guia, seção 8.2)
- [x] Interfaces (portas) dos repositórios (issue #46): `ClienteRepository`, `VeiculoRepository`, `UsuarioRepository`, `ServicoRepository`, `PecaRepository`, `EstoqueRepository` e `OrdemServicoRepository`, esta com a consulta das OS que têm a peça pendente, na ordem da abertura

### Testes

- [x] Testes unitários dos objetos de valor, da máquina de estados, do cálculo do orçamento, da estimativa de entrega e das regras de estoque, usando repositórios em memória de todas as portas, em `tests/unit/conftest.py` (RNF-12; issue #47). Só com os testes unitários, sem banco, `src/domain` tem 100% de cobertura (RNF-14).

---

## Fase 4 - Autenticação e Cadastros Administrativos

**Objetivo:** disponibilizar o acesso autenticado com controle por perfil e os cadastros que alimentam a Ordem de Serviço.

**Ponto de partida:** a autenticação já está implementada, distribuída pelas camadas conforme a seção 5 de [estrutura-de-pastas.md](docs/estrutura-de-pastas.md) (portas `TokenService` e `PasswordHasher`, caso de uso `autenticar_usuario.py`, adaptadores de JWT e bcrypt e `presentation/middlewares/dependencies.py`).

- [x] Login com e-mail e senha, emitindo JWT com a claim `role` e expiração de 24 horas (RF-01)
- [x] Guard de RBAC retornando `401` sem token válido e `403` sem permissão (RF-02, RNF-03): `obter_usuario_autenticado` e `exigir_perfis` em `presentation/middlewares/dependencies.py`
- [x] Gestão de usuários internos exclusiva do Gerente, com senhas em hash bcrypt (RF-03; issue #81)
- [x] Carga inicial do Gerente na subida do container, com `ADMIN_PASSWORD` obrigatória, e dos usuários de demonstração quando `SEED_DEMO=true` (RF-03)
- [x] Cadastro, atualização e listagem de clientes, com validação de CPF/CNPJ (RF-04, RF-05; issue #82)
- [x] Exclusão lógica de clientes pelo Gerente (RF-06; issue #82)
- [x] Cadastro, atualização e listagem de veículos vinculados ao cliente, com validação de placa (RF-07, RF-08; issue #83)
- [x] Exclusão lógica de veículos por Atendente e Gerente (RF-09; issue #83)
- [x] Listagem do catálogo de serviços (RF-10) e CRUD restrito ao Gerente, com tempo estimado e exclusão lógica (RF-11; issue #84)
- [x] Gestão de peças, com prazo de reposição, exclusão lógica (recusada com OS pendente) e atualização de saldo com permissões por perfil (RF-12; issue #85). A recusa com OS pendente é coberta pela rota desde a persistência da OS (issue #88); a alocação do saldo às OS com peça pendente fica com o handler da Fase 5 (RF-19; issue #94)
- [x] Testes de integração das rotas, com banco PostgreSQL real (RNF-13): os fluxos de cada recurso em `test_fluxo_*.py` e a matriz perfis × rotas em `test_permissoes_das_rotas.py`, com acesso sem token, com token malformado ou expirado (`401`) e com perfil sem permissão (`403`) em todas as rotas da Fase 4 (issue #87)

---

## Fase 5 - Fluxo da Ordem de Serviço

**Objetivo:** implementar o fluxo central do sistema, da abertura à entrega do veículo.

### Frente da Loja

- [x] Abertura da OS com status `RECEBIDA` e número `DDD-XXXXXXXX`, carregando cliente e veículo existentes ou cadastrando-os no mesmo fluxo (RF-13, RF-04, RF-07; issue #90)
- [x] Atribuição do mecânico com transição para `EM_DIAGNOSTICO` (RF-16; issue #91)
- [x] Inclusão de serviços e peças e conclusão do orçamento, com transição para `AGUARDANDO_APROVACAO` (RF-17; issue #92). A conclusão despacha o `OrcamentoFinalizadoEvent` na mesma transação; a reserva das peças que reage a ele é a issue #93
- [x] Reserva das peças com registro de pendências e prioridade pela OS mais antiga (RF-18; issue #93): o `ReservaPecasHandler` trata o `OrcamentoFinalizadoEvent` na transação da conclusão
- [x] Alocação automática das peças repostas e liberação de OS de `AGUARDANDO_PECA` para `AGUARDANDO_EXECUCAO` (RF-19; issue #94): o `AlocacaoPecasPendentesHandler` trata o `SaldoPecaAtualizadoEvent` da reposição e do ajuste para cima, na transação da operação
- [x] Início da execução pelo mecânico atribuído ou pelo Gerente, com baixa das peças (RF-20; issue #99): `POST /ordens-servico/{id}/execucao`; o `ExecucaoIniciadaEvent` é tratado pelo `BaixaEstoqueHandler` na transação, que reduz a quantidade física e a reservada; outro mecânico recebe `403`
- [x] Conclusão da manutenção com transição para `FINALIZADA` (RF-21; issue #100): `POST /ordens-servico/{id}/conclusao`, só para o mecânico atribuído ou o Gerente (`403` para outro mecânico); `concluir_manutencao` passou a receber o `Usuario`; os itens ficam bloqueados depois da finalização (`422`)
- [ ] Entrega do veículo com transição para `ENTREGUE`, restrita a Atendente e Gerente (RF-22)
- [x] Cancelamento pelo Gerente, com motivo no histórico e estorno das reservas (RF-23, RF-18; issue #95): `POST /ordens-servico/{id}/cancelamento`, só para o Gerente; o `OSCanceladaEvent` é tratado pelo `EstornoReservasHandler` na transação, e o saldo devolvido segue para a alocação às OS que esperam a peça. O motivo com `<` responde `400` (RNF-04). Os impasses entre a alocação e o cancelamento são repetidos pela unidade de trabalho, em até 3 tentativas
- [x] Registro de toda transição no histórico de status (RF-24; issue #88): tabela só com inserção, protegida por trigger

### Frente do Cliente

- [ ] Consulta pública por número da OS + CPF/CNPJ, com estimativa de entrega e sem expor dados pessoais sensíveis (RF-25, RNF-04)
- [ ] Rate limiting com SlowAPI nas rotas públicas (10 requisições por minuto por IP) (RNF-05)
- [ ] Aprovação do orçamento com transição para `AGUARDANDO_EXECUCAO` ou `AGUARDANDO_PECA` (RF-26)
- [ ] Rejeição do orçamento com transição para `CANCELADA` e estorno automático das reservas (RF-26, RF-18)
- [ ] Garantir que a transição de status e a movimentação de estoque ocorram na mesma transação, inclusive quando disparadas por eventos (RNF-08)

### Testes

- [ ] Teste de integração do fluxo completo: abertura → diagnóstico → orçamento → aprovação → fila de execução → execução → finalização → entrega (RNF-13)
- [ ] Teste de integração da aprovação com peça pendente e da liberação pela reposição de estoque, incluindo a prioridade entre duas OS (RNF-13)
- [ ] Testes de integração dos fluxos de rejeição e de cancelamento, verificando o estorno das reservas (RNF-13)
- [x] (Recomendado) Teste de concorrência com duas reservas disputando a mesma peça (RNF-09; issue #106)

---

## Fase 6 - Gestão e Métricas

**Objetivo:** fornecer as visões administrativas sobre as Ordens de Serviço.

- [x] Listagem de OS com filtros por status, mecânico, CPF/CNPJ ou placa e período de abertura (RF-14; issue #107)
- [x] Detalhamento da OS com histórico, cliente, veículo, itens, pendências, valores e estimativa de entrega (RF-15)
- [ ] Relatório de tempos médios restrito ao Gerente: execução por período e por mecânico, espera por peça e tempo total da OS (RF-27)
- [ ] Testes de integração das rotas (RNF-13)

---

## Fase 7 - Qualidade e Segurança

**Objetivo:** consolidar as evidências de qualidade e segurança exigidas na entrega.

- [ ] Cobertura ≥ 80% nos módulos de domínio e aplicação, medida com `pytest-cov` (RNF-14)
- [ ] Evidência da cobertura salva (relatório ou captura de tela) para uso no README e no vídeo
- [x] Análise de vulnerabilidades de dependências, código e imagem Docker, com correção do que for encontrado (RNF-07; issue #111). Refazer no commit final
- [x] Relatório da análise de vulnerabilidades salvo em `docs/security/` (RNF-07; `docs/security/analise-de-vulnerabilidades.md`)
- [ ] Revisão das proteções contra SQL Injection, IDOR e XSS (RNF-04) e do rate limiting (RNF-05)
- [ ] Medição do tempo de resposta (p95 < 500 ms) com evidência registrada (RNF-10)
- [x] Revisão do repositório: nenhum segredo, senha ou token no código ou no histórico do git (RNF-06; issue #114, `docs/security/revisao-de-segredos.md`). Repetir no commit final
- [ ] Revisão do Swagger: schemas de entrada e saída, códigos HTTP e autenticação Bearer (RNF-16)

---

## Fase 8 - Documentação e Entrega

**Objetivo:** reunir tudo o que será avaliado. A correção considera apenas o commit informado no PDF de entrega.

### README.md

- [x] Objetivo do projeto
- [x] Descrição resumida da solução
- [x] Arquitetura utilizada (pode referenciar o [modelo C4](docs/ddd/c4-model.md))
- [x] Tecnologias utilizadas
- [x] Pré-requisitos
- [x] Instruções para execução, incluindo a cópia do `.env.example` para `.env` e o preenchimento das variáveis obrigatórias
- [x] Instruções para execução dos testes
- [x] Instruções de acesso ao Swagger (`/docs`)
- [x] Decisão e justificativa do banco de dados (pode reaproveitar o RNF-09)
- [x] Usuários de demonstração (`SEED_DEMO=true`) e procedimento de autenticação
- [ ] Estrutura dos principais diretórios (pode reaproveitar o guia de desenvolvimento)
- [ ] Link para a documentação DDD
- [ ] Link para o vídeo da entrega

### Documentação DDD

- [ ] Conferir se o board, os PDFs exportados e os diagramas correspondem ao código final
- [ ] Atualizar o mapeamento entre documentação e código na linguagem ubíqua

### Vídeo

Publicado no YouTube como **público**, com no máximo **15 minutos**, áudio compreensível e identificação dos integrantes.

- [ ] Roteiro cobrindo os pontos exigidos: proposta da solução, arquitetura, organização do monólito e camadas, escolha do banco de dados, Event Storming, elementos de DDD, criação e acompanhamento da OS, inclusão de serviços/peças/insumos, geração e aprovação do orçamento, alteração de status, autenticação das APIs administrativas, execução da aplicação, Swagger, testes automatizados e análise de vulnerabilidades
- [ ] Gravação com a aplicação rodando na versão do commit final
- [ ] Publicação e teste do link

### PDF de Entrega

- [ ] Primeira página: curso (SOAT - Software Architecture), fase 1, número do grupo, nome completo e RM de todos os integrantes, usernames do Discord, linguagem e principais tecnologias
- [ ] Links clicáveis do repositório, do vídeo e do board do Event Storming
- [ ] Branch e hash do commit final (recomendado: criar também uma tag, ex.: `v1.0-fase1`)
- [ ] Testar todos os links em uma janela anônima antes do envio

---

## Definição de Pronto

Uma tarefa de código só é considerada concluída quando:

- foi integrada à `main` via Pull Request revisado por outro integrante, citando os requisitos atendidos (guia de desenvolvimento, seção 7);
- respeita a regra de dependência entre camadas (guia de desenvolvimento, seção 2.1);
- possui testes unitários e/ou de integração passando, incluindo as permissões por perfil quando houver rota protegida;
- o endpoint está refletido corretamente no Swagger;
- a linguagem ubíqua foi atualizada, caso algum termo do domínio tenha surgido ou mudado;
- não introduz segredos no repositório.
