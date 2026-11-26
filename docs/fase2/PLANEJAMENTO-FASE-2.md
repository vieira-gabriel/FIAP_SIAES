# Planejamento – Tech Challenge Fase 2 (SIAES)

> **Documento histórico.** As decisões deste planejamento foram fechadas em 25/11/2026 e registradas nos [ADRs](../adr/README.md). Para a execução da Fase 2, o [blueprint](BLUEPRINT-FASE-2.md) prevalece sobre este documento.

> Rascunho para leitura do grupo. Nada aqui foi implementado ainda.
> Base: PDF `DocsFiap/SOAT - Fase 2 - Tech challenge.pdf` + leitura do repositório da Fase 1 (`E:\Projeto FIAP\Tech Challenge 1`, remoto `vieira-gabriel/FIAP_SIAES`).
> Este documento traz **dois planos de arquitetura completos** (Clean Architecture e Hexagonal) para o grupo escolher. Tudo que não depende dessa escolha (APIs, Docker, K8s, Terraform, CI/CD, README, vídeo) está na Parte C e vale para as duas.

---

## Sumário

- [A. O que a FIAP pede](#a-o-que-a-fiap-pede)
- [B. Ponto de partida: o que a Fase 1 já tem e o que falta](#b-ponto-de-partida)
- [C. Trabalho comum às duas arquiteturas](#c-trabalho-comum-às-duas-arquiteturas)
- [D. Plano 1 – Clean Architecture](#d-plano-1--clean-architecture)
- [E. Plano 2 – Arquitetura Hexagonal](#e-plano-2--arquitetura-hexagonal)
- [F. Comparativo e recomendação](#f-comparativo-e-recomendação)
- [G. Decisões que o grupo precisa tomar](#g-decisões-que-o-grupo-precisa-tomar)
- [H. Fases de execução](#h-fases-de-execução)
- [I. Riscos](#i-riscos)
- [J. Checklist final de entrega](#j-checklist-final-de-entrega)

---

## A. O que a FIAP pede

**Contexto do enunciado:** a oficina cresceu, vai abrir novas unidades e precisa de alta disponibilidade, deploy automatizado e escalabilidade dinâmica em horários de pico. Vale **60% da nota de todas as disciplinas da fase**, então a entrega é obrigatória.

### A.1 Requisitos obrigatórios

| # | Eixo | Exigência literal (resumida) |
| :-- | :-- | :-- |
| 1 | Refatoração | Clean Code + (Clean Architecture **ou** Hexagonal) + testes automatizados (unitários e/ou integração) nos fluxos críticos |
| 2 | API | **Abertura de OS**: recebe dados de cliente, veículo, serviços e peças; devolve identificação única da OS |
| 3 | API | **Consulta de status** da OS (Recebida, Diagnóstico, Aguardando Aprovação, Execução, Finalizada, Entregue) |
| 4 | API | **Aprovação de orçamento**: endpoint que recebe **notificações externas** de aprovação ou recusa |
| 5 | API | **Listagem de OS**: ordenar por status (Em Execução > Aguardando Aprovação > Diagnóstico > Recebida), mais antigas primeiro; **excluir da listagem** (lógica) as OS finalizadas e entregues |
| 6 | API | **Atualização de status da OS via ferramenta como e-mail** |
| 7 | Docker | Dockerfile atualizado + docker-compose para desenvolvimento local |
| 8 | K8s | Manifestos YAML: Deployments, Services, ConfigMaps, Secrets, **HPA** (CPU/memória) |
| 9 | IaC | Terraform para o cluster Kubernetes (local ou nuvem) e o banco de dados; documentar recursos e como aplicar |
| 10 | CI/CD | Pipeline com: build, testes, build da imagem Docker, deploy no cluster, deploy do banco, aplicação dos manifestos |

### A.2 Entregáveis

- **Repositório git (o mesmo da Fase 1)** com: código refatorado; Dockerfile + compose; manifestos em **`/k8s`**; Terraform em **`/infra`**; arquivos da pipeline.
- **README.md** atualizado com: descrição da solução e dos objetivos da fase; **desenho da arquitetura** (componentes, infraestrutura provisionada, fluxo de deploy); instruções de execução local, deploy em K8s e Terraform; **link da collection das APIs** (Postman/Swagger); **link do vídeo** (YouTube/Vimeo, público ou não listado, **até 15 min**).
- **Vídeo** deve mostrar: deploy da aplicação, execução do CI/CD, consumo das APIs, escalabilidade automática (pode simular carga).
- **Portal do aluno:** PDF com link do repositório **compartilhado com o usuário `soat-architecture`**, desenho da arquitetura com os recursos escolhidos e link do vídeo.

> **Prazo informado: 19/01 (terça-feira de 2027, assumido).** A data escrita foi 19/01/2026, que já passou; o ano deve ser 2027. Se o prazo real for outro, ajustem a Parte H.

---

## B. Ponto de partida

### B.1 O que a Fase 1 já entrega (verificado no repositório)

- Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL 16, Alembic (7 migrations), JWT + RBAC, rate limit (slowapi), uv.
- Estrutura em camadas `domain / application / infrastructure / presentation`, com regra de dependência para dentro **já documentada** em `docs/guia-de-desenvolvimento.md` (domínio em Python puro, portas ABC, adaptadores em `infrastructure`, `container.py` como único ponto que conhece as implementações).
- ~60 casos de uso (um arquivo por caso), agregado `OrdemServico` com máquina de estados e histórico, eventos de domínio com `EventDispatcher` **síncrono em memória** e handlers (reserva, baixa, estorno de peças).
- Dockerfile multi-stage (usuário não-root), `docker-compose.yml` (app + postgres), CI no GitHub Actions (ruff, pytest com Postgres, cobertura ≥ 80%, bandit, pip-audit, build da imagem).
- Documentação extensa (RF/RNF, DDD, C4, event storming) e a suíte de testes unitários e de integração (o README cita 1872 testes).
- Já existe um cenário **Locust** em `tests/desempenho/` — serve para demonstrar o HPA no vídeo.
- `AGENTS.md`/`CLAUDE.md` com regras de trabalho (issues, PRs, changelog de documentação). **Vamos seguir essas regras também na Fase 2.**

### B.2 Mapa do enunciado contra o que existe (lacunas)

| Exigência | Situação hoje | Trabalho |
| :-- | :-- | :-- |
| Abertura de OS com cliente, veículo, **serviços e peças** | `POST /ordens-servico` abre a OS em `RECEBIDA` só com documento + placa (+ cliente/veículo novos). Serviços e peças entram depois, em rotas separadas, durante o diagnóstico | Estender o corpo (ou criar rota composta) para aceitar serviços e peças já na abertura; ver G-3 |
| Consulta de status | Existe `POST /acompanhamento` (público, exige nº da OS + CPF/CNPJ) e `GET /ordens-servico/{id}` (autenticado) | Provavelmente só ajustar o contrato/documentação; avaliar um `GET .../status` enxuto |
| Aprovação por **notificação externa** | `POST /acompanhamento/aprovacao` (cliente com CPF) e `POST /ordens-servico/{id}/orcamento/aprovacao` (balcão) | Criar endpoint de **webhook** autenticado por chave/assinatura, idempotente, sem exigir CPF no corpo |
| Listagem ordenada por prioridade, antigas primeiro, sem finalizadas/entregues | `GET /ordens-servico` ordena **mais recentes primeiro** (RF-14) e lista tudo | Mudar a ordenação e o filtro padrão; **muda um requisito da Fase 1** (atualizar RF-14 e testes) |
| Atualização de status por e-mail | Não existe nenhum código de e-mail | Nova porta de notificação + adaptador SMTP; ver C.2 |
| Docker/compose | Existem e funcionam | Revisar (healthcheck, migração, Mailpit, variáveis novas) |
| `/k8s` | Não existe | Criar |
| `/infra` (Terraform) | Não existe | Criar |
| CI/CD com deploy | CI existe; **CD não** | Criar jobs de build/push da imagem e deploy |
| README da Fase 2, collection, vídeo | README é da Fase 1 | Atualizar |

### B.3 Observações de arquitetura relevantes para o K8s

Pontos do código atual que mudam de comportamento ao rodar **várias réplicas**:

1. **Migration no startup:** o `CMD` do Dockerfile roda `alembic upgrade head` antes do uvicorn. Com N réplicas subindo juntas, há corrida. → mover para **Job do K8s** (ou initContainer com lock).
2. **Rate limit do slowapi** é em memória por processo: o limite vira "por pod". → documentar a limitação ou usar storage compartilhado (Redis) – provavelmente fora de escopo; documentar.
3. **EventDispatcher síncrono** roda dentro da transação: seguro com várias réplicas (a concorrência já é tratada com lock no banco – RNF-08/09, teste `test_concorrencia_da_reserva`). Mas **e-mail não pode rodar dentro dessa transação** (ver C.2).
4. **Seed (`ADMIN_PASSWORD`, `JWT_SECRET_KEY`, senhas do banco):** vão para **Secret**; a aplicação já falha sem elas, o que combina com `readinessProbe`.
5. `/health` já existe → base para `liveness`/`readiness` probes.

> Nota prática: a pasta `Tech Challenge 2` só tem o PDF. Como o entregável é **o mesmo repositório**, o código será alterado no clone da Fase 1 (em branches novas), e esta pasta fica como espaço de documentação/planejamento. Confirmem isso na G-1.

---

## C. Trabalho comum às duas arquiteturas

### C.1 Mudanças de API (detalhe)

| API | Proposta | Observações |
| :-- | :-- | :-- |
| **Abrir OS** | `POST /ordens-servico` aceita opcionalmente `servicos: [{codigo, ...}]` e `pecas: [{codigo, quantidade}]`; devolve `id` (UUID) e `numero` | Reaproveitar os casos de uso `IncluirServicoNaOS`/`IncluirPecaNaOS` na orquestração; a abertura precisa ser atômica (tudo ou nada). Decidir se a OS já nasce com orçamento (G-3) |
| **Consultar status** | Manter `POST /acompanhamento` (público) e documentar; opcional `GET /ordens-servico/{id}/status` autenticado | Mapear os 9 status internos para os 6 do enunciado na resposta/documentação (G-4) |
| **Aprovação externa** | `POST /webhooks/orcamento` (nome a definir) com corpo `{numero_os, decisao: APROVADO/RECUSADO, id_notificacao}` | Autenticação por **API key** ou **HMAC** em header (secret no K8s Secret); idempotência pelo `id_notificacao`; 404/422 consistentes com o fluxo atual; reusa `AprovarOrcamento`/`RejeitarOrcamento` |
| **Listagem** | `GET /ordens-servico` passa a: (1) excluir `FINALIZADA`, `ENTREGUE` (e decidir `CANCELADA`) por padrão; (2) ordenar por prioridade de status; (3) dentro do status, `data_abertura` ascendente | Implementar a prioridade **no banco** (`CASE`/coluna de ordem) para funcionar com paginação. Adicionar paginação. Manter um parâmetro para incluir encerradas (uso do gerente/relatórios) |
| **Atualização de status por e-mail** | Ver C.2 | |

**Ordenação – lacuna do enunciado:** ele lista 4 status, mas o sistema tem 9. Proposta para o grupo validar (G-4):

1. `EM_EXECUCAO`
2. `AGUARDANDO_APROVACAO`
3. `EM_DIAGNOSTICO`
4. `RECEBIDA`
5. (proposta) `AGUARDANDO_EXECUCAO` e `AGUARDANDO_PECA` entram **logo abaixo de `EM_EXECUCAO`**, porque já foram aprovadas e estão a caminho da execução – ou ficam no fim, após `RECEBIDA`.
6. `FINALIZADA`, `ENTREGUE` (e `CANCELADA`) fora da listagem padrão.

### C.2 Atualização de status por e-mail

O enunciado é ambíguo ("atualização de status da OS via alguma ferramenta como e-mail"). Interpretação recomendada: **notificação de saída** – quando o status da OS muda, o cliente recebe um e-mail (isso é a "ferramenta" que informa a atualização). Interpretação alternativa: **entrada** por e-mail (cliente responde "APROVO"). Ela é bem mais cara (caixa postal, parsing) e o endpoint de webhook já cobre a "notificação externa" do item 4. → Proposta: fazer a saída, e o webhook de aprovação cobre a entrada. Levar ao professor se houver dúvida (G-5).

Desenho:

- **Porta** `NotificadorDeStatus` (ou `NotificadorDeCliente`) recebendo cliente, OS, status anterior/novo.
- **Adaptador SMTP** (`smtplib`/`aiosmtplib`), com host/usuário/senha em ConfigMap/Secret. Em desenvolvimento: **Mailpit** no docker-compose (captura e mostra os e-mails em uma UI web – ótimo para o vídeo). Em nuvem: provedor SMTP real (ex.: SES, SendGrid, Gmail com senha de app).
- **Quando enviar:** hoje o `EventDispatcher` é síncrono e **dentro da transação**; enviar e-mail ali faria uma falha de SMTP desfazer a transição da OS e deixaria a requisição lenta. Opções, da mais simples à mais robusta:
  1. **Handler pós-commit** (despachar eventos de notificação só depois do commit, falha apenas registrada em log). *Recomendada para o prazo.*
  2. **Outbox**: gravar a notificação em tabela na mesma transação e um worker/CronJob enviar. Mais robusta; mais trabalho (nova migration + processo).
- Novos eventos de domínio (por ex. `StatusOSAlteradoEvent`) emitidos por `_mudar_status`, já que hoje só alguns status emitem evento.
- Testes: unitário com notificador *fake*; integração com Mailpit/servidor SMTP de teste.

### C.3 Docker e docker-compose

- Revisar o Dockerfile (já é multi-stage, não-root, sem pip). Ajustes: separar o comando de migration do de execução (para o Job do K8s), `HEALTHCHECK`/probes, tag de versão.
- `docker-compose.yml`: app + db + **mailpit**; variáveis novas no `.env.example`; manter o `docker-compose.testes.yml`.
- Opcional: perfil `migrate` que roda o Alembic como serviço único.

### C.4 Kubernetes (`/k8s`)

Estrutura proposta (Kustomize simples, para suportar `local` e `cloud` sem duplicar YAML):

```text
k8s/
├── base/
│   ├── namespace.yaml
│   ├── configmap.yaml            variáveis não sensíveis (host do banco, SMTP_HOST, LOG_LEVEL...)
│   ├── secret.example.yaml       modelo; o Secret real NÃO vai para o git (criado pelo pipeline)
│   ├── deployment-api.yaml       replicas, resources requests/limits, probes /health, env do ConfigMap/Secret
│   ├── service-api.yaml          ClusterIP (+ Ingress ou LoadBalancer)
│   ├── hpa-api.yaml              autoscaling/v2, CPU (e memória), min 2 / max 6
│   ├── job-migration.yaml        alembic upgrade head antes do rollout
│   ├── ingress.yaml              (opcional)
│   └── postgres/                 só no overlay local (StatefulSet + PVC + Service)
├── overlays/
│   ├── local/                    kind/minikube: Postgres no cluster, NodePort/port-forward
│   └── cloud/                    banco gerenciado (Terraform), LoadBalancer/Ingress
└── README.md
```

Pontos de atenção do HPA: exige `resources.requests` nos containers e **metrics-server** instalado (vem no minikube via addon; no kind precisa instalar; em EKS/AKS/GKE costuma estar ou ser addon).

### C.5 Terraform (`/infra`)

O PDF permite cluster **local ou nuvem**. Mas a pipeline precisa **fazer deploy no cluster**, e um cluster local não é alcançável pelos runners hospedados do GitHub. Opções:

| Opção | O que o Terraform cria | Prós | Contras |
| :-- | :-- | :-- | :-- |
| **1. AWS** | VPC, **EKS**, **RDS PostgreSQL**, ECR, IAM/roles, (opcional SES) | Padrão de mercado, CD real, cobre "cluster + banco" | Custo (EKS ~US$ 0,10/h + nós + NAT + RDS); contas educacionais (Learner Lab) costumam **restringir** EKS/IAM |
| **2. Azure** | Resource Group, **AKS**, **Azure Database for PostgreSQL Flexible**, ACR | Créditos para estudante; AKS control plane gratuito | Cota/regiões; menos comum no grupo? |
| **3. GCP** | GKE, Cloud SQL, Artifact Registry | GKE Autopilot simples | Cartão/créditos |
| **4. Local (kind/minikube)** | Provider `kubernetes`/`helm` (e/ou `kind`) instala namespace, metrics-server, Postgres | Custo zero, simples de demonstrar | CD exige **runner self-hosted** na máquina ou apenas "simular" o deploy; é o item mais fraco no critério "deploy no cluster" |
| **5. Misto** | Terraform de **nuvem** como entrega "oficial" + overlay local para desenvolver/demonstrar | Melhor cobertura da avaliação | Mais trabalho (duas rotas) |

**Recomendação provisória:** Opção 5 – desenvolver e validar localmente em kind/minikube (custo zero), e entregar o Terraform e o CD em **uma nuvem** que o grupo tenha acesso. Qual nuvem e quais créditos é a decisão G-2 mais importante, porque dela dependem `/infra`, o CD e o desenho de arquitetura do PDF.

Documentar em `infra/README.md`: lista de recursos criados, variáveis, `terraform init/plan/apply/destroy`, custos estimados e **como destruir** (evitar cobrança após a nota). *State remoto* (bucket) opcional; no mínimo documentar. Nunca versionar `*.tfstate` nem `*.tfvars` com segredos.

### C.6 CI/CD (GitHub Actions)

Evoluir o `ci.yml` atual (que já faz lint, testes, cobertura, bandit, pip-audit e build da imagem) e criar o CD:

```text
PR / push:       lint → testes (unit + integração c/ Postgres) → cobertura ≥ 80% → segurança → build da imagem
push na main:    ... acima → push da imagem no registry (tag = SHA)
                 → configura acesso ao cluster (OIDC / secret de kubeconfig)
                 → terraform apply (ou só plan/validate, conforme G-2)
                 → cria/atualiza ConfigMap e Secret a partir dos GitHub Secrets
                 → roda Job de migration (deploy do banco/esquema)
                 → kubectl apply -k k8s/overlays/cloud  (manifestos)
                 → kubectl rollout status + smoke test em /health
```

A exigência "Deploy do banco de dados" é atendida por: banco provisionado pelo Terraform **e** migrations aplicadas pelo Job a cada deploy. Segredos apenas em **GitHub Secrets/Environments** (o repo já tem `gitleaks`/`RNF-06` como padrão). Considerar *environment* com aprovação manual para o deploy.

### C.7 Testes

- Manter a suíte da Fase 1 verde durante toda a refatoração (é a rede de segurança).
- Novos testes: abertura de OS composta, ordenação/filtro da listagem (incluindo empate por data), webhook (autenticação inválida, idempotência, decisão duplicada), notificação de e-mail (sucesso e falha não derrubando a transição).
- Teste de arquitetura (regra de dependência) automatizado, p.ex. `import-linter` ou um teste que varre os imports – serve como evidência da arquitetura escolhida no vídeo/README.
- Cobertura ≥ 80% mantida (hoje o `coverage` mede só `domain` e `application`; considerar incluir os novos adaptadores).

### C.8 Documentação e vídeo

- **README da Fase 2:** objetivos, diagrama (Mermaid) de componentes + infraestrutura + fluxo de deploy, passo a passo de execução local, K8s e Terraform, link Swagger/Postman, link do vídeo.
- **Collection Postman** exportada para `docs/` (ou usar o Swagger/OpenAPI que o FastAPI já gera – o enunciado aceita "Swagger ou similar").
- **Desenho de arquitetura** como imagem/PDF também para o portal.
- Atualizar `docs/` (RF novos, RNF de infra, C4, CHANGELOG – regra do `AGENTS.md`).
- **Roteiro do vídeo (≤ 15 min):** (1) arquitetura em 2 min; (2) `terraform apply`/cluster no ar; (3) push que dispara o CI/CD até o deploy; (4) chamadas das APIs (abrir OS, consultar, webhook de aprovação, listagem, e-mail chegando no Mailpit/caixa); (5) Locust gerando carga e `kubectl get hpa -w` mostrando as réplicas subirem. Gravar um ensaio antes.

---

## D. Plano 1 – Clean Architecture

### D.1 Ideia central

Círculos concêntricos com a **regra de dependência apontando para dentro**: Entities → Use Cases → Interface Adapters → Frameworks & Drivers. As camadas internas nunca conhecem as externas; a comunicação para fora é por **interfaces definidas na camada interna** (inversão de dependência) e por **DTOs simples** nas fronteiras.

### D.2 Avaliação da Fase 1 contra Clean Architecture

O que **já cumpre** (verificado pelo guia e pela estrutura de pastas):

- `domain` puro (entidades, VOs, eventos, exceções) – círculo 1.
- `application/use_cases` com portas (`TokenService`, `PasswordHasher`, `UnidadeDeTrabalho`) e repositórios como ABC – círculo 2.
- `infrastructure` implementa as portas; `presentation` entrega HTTP; composição em `container.py`.

O que **falta ou é discutível** (hipóteses a confirmar lendo o código com calma na Fase H-1):

1. As rotas devolvem DTOs montados **a partir de entidades** (`OSResponse.de_entidade(os)`): a camada de apresentação conhece o interior do domínio. Em Clean "pura", os casos de uso devolvem **DTOs de saída (Output Data)** e o presenter/controller só os traduz. Dá para fazer só nos casos de uso que vamos mexer (abertura, listagem, aprovação) e padronizar daqui para frente.
2. Interfaces de repositório estão em `domain/repositories`. Em Clean isso é aceitável (são "gateways" do domínio), então **pode ficar**.
3. `presentation/routers/ordens_servico.py` concentra lógica de montagem de critérios/conversão (VOs, `Documento.de_texto`, etc.). Mover a conversão para um *controller/mapper* fino.
4. `container.py` fica em `presentation`: Clean coloca a composição na camada mais externa (*main component*). Pode virar `src/main/` (composition root) em vez de dentro de `presentation`.
5. Nomes: já seguem a Linguagem Ubíqua; manter.

### D.3 Estrutura-alvo

```text
src/
├── domain/                     CÍRCULO 1 – Enterprise Business Rules
│   ├── entities/ value_objects/ events/ exceptions.py
│   └── repositories/           gateways (interfaces) de persistência        [mantém]
├── application/                CÍRCULO 2 – Application Business Rules
│   ├── use_cases/              um por caso de uso                           [mantém]
│   ├── dtos/                   NOVO: Input/Output dos casos de uso (dataclasses puras)
│   ├── ports/                  interfaces técnicas: token, hash, UoW,
│   │                           NotificadorDeStatus (NOVO), VerificadorDoBanco
│   ├── events/ handlers/       dispatcher e handlers                        [mantém]
├── interface_adapters/         CÍRCULO 3 (renomear/dividir presentation e parte de infra)
│   ├── controllers/            traduz request → Input DTO, chama caso de uso   (NOVO/extraído dos routers)
│   ├── presenters/             Output DTO → response model da API              (substitui `de_entidade`)
│   └── gateways/               adaptadores de persistência (repos Postgres) e de e-mail
├── infrastructure/             CÍRCULO 4 – Frameworks & Drivers
│   ├── web/                    FastAPI app, routers finos, middlewares, rate limit, interface web
│   ├── database/               engine, models SQLAlchemy, UoW
│   ├── notifications/          SMTP (NOVO)
│   └── config.py
└── main/                       composition root (container + montagem do app)
```

> Alternativa **mais leve**: manter os 4 diretórios atuais e só acrescentar `application/dtos`, `application/ports/notificador_de_status.py` e extrair controllers/presenters dentro de `presentation/`. Entrega a mesma qualidade percebida com muito menos *rename*. O grupo escolhe o grau de purismo (G-6).

### D.4 Como os novos itens se encaixam

| Item | Camada | Arquivos (exemplo) |
| :-- | :-- | :-- |
| Abertura de OS composta | use case + DTOs | `application/use_cases/abrir_os_completa.py`, `application/dtos/abertura_os.py` |
| Ordenação/filtro da listagem | critérios no domínio/VO; consulta no gateway | `domain/value_objects/prioridade_status.py` (regra de negócio!), `PostgresOrdemServicoRepository` aplica |
| Webhook de aprovação | controller + caso de uso existente | rota em `infrastructure/web/routers/webhooks.py`; dependência de verificação de assinatura em `middlewares/` |
| E-mail | porta + gateway + handler | `application/ports/notificador_de_status.py`; `infrastructure/notifications/smtp_notificador.py`; `application/handlers/notificar_cliente_handler.py` |

### D.5 Etapas da refatoração (Clean)

1. **Linha de base:** rodar a suíte inteira, registrar a cobertura, criar o teste automatizado da regra de dependência.
2. Criar `application/dtos` e adotar **Output DTOs** primeiro nos casos de uso que serão alterados; depois migrar os demais por recurso (clientes, veículos, serviços, peças, usuários) em PRs pequenos.
3. Extrair controllers/presenters dos routers (um recurso por PR).
4. Mover o container para a *composition root* (se optarem pela estrutura completa).
5. Implementar os requisitos novos (Parte C) **já no novo molde**.
6. Atualizar `docs/guia-de-desenvolvimento.md`, `estrutura-de-pastas.md`, C4 e CHANGELOG.

**Esforço relativo:** médio. **Risco de regressão:** baixo-médio (as camadas internas quase não mudam; o grosso é fronteira HTTP).

---

## E. Plano 2 – Arquitetura Hexagonal

### E.1 Ideia central

O **núcleo (domínio + aplicação)** fica no centro e se comunica com o mundo por **portas**. **Portas de entrada (driving/primary)** definem o que o sistema oferece (casos de uso); **portas de saída (driven/secondary)** definem do que o sistema precisa (persistência, e-mail, token). **Adaptadores** conectam tecnologias às portas: HTTP, CLI, webhooks de um lado; Postgres, SMTP, JWT do outro. A distinção explícita entre *entrada* e *saída* e a simetria dos adaptadores são a marca registrada.

### E.2 Avaliação da Fase 1 contra Hexagonal

O que **já cumpre:**

- Portas de saída existem como ABCs (repositórios, `TokenService`, `PasswordHasher`, `UnidadeDeTrabalho`) e adaptadores concretos em `infrastructure`.
- O núcleo é independente de framework.

O que **falta:**

1. **Portas de entrada explícitas:** hoje o FastAPI chama diretamente a classe do caso de uso. Em Hexagonal, cada caso de uso implementa uma interface de entrada (`AbrirOSPort`, `ListarOSPort`...) e os adaptadores dependem dela. É mais cerimônia (~60 interfaces) — recomendo criar portas de entrada **por agrupamento/serviço** ou só para os casos centrais, não para os 60 (G-6).
2. **Separação física driving × driven:** hoje existe `infrastructure` (saída) e `presentation` (entrada) como irmãos. Hexagonal pede `adapters/inbound` e `adapters/outbound`.
3. Portas de saída ficam espalhadas (`domain/repositories` e `application/ports`). Centralizar em `ports/outbound`.
4. Adaptadores de entrada além de HTTP: o **webhook** e o **e-mail** são adaptadores distintos – encaixa bem no modelo.

### E.3 Estrutura-alvo

```text
src/
├── core/                              O HEXÁGONO
│   ├── domain/                        entidades, VOs, eventos, exceções          [move de domain/]
│   ├── ports/
│   │   ├── inbound/                   interfaces dos casos de uso (driving)       (NOVO)
│   │   │     abrir_os.py  consultar_status_os.py  listar_os.py  decidir_orcamento.py ...
│   │   └── outbound/                  interfaces do que o núcleo precisa (driven)
│   │         repositorios/ (os, cliente, veiculo, servico, peca, estoque, usuario)
│   │         token_service.py  password_hasher.py  unidade_de_trabalho.py
│   │         notificador_de_status.py (NOVO)
│   └── application/                   implementação dos casos de uso (services) + handlers + dispatcher
│         use_cases/  handlers/  events/
├── adapters/
│   ├── inbound/                       quem CHAMA o sistema
│   │   ├── http_rest/                 FastAPI: routers, schemas, middlewares, auth      [de presentation/]
│   │   ├── http_webhook/              webhook de aprovação externa (NOVO, com assinatura)
│   │   └── web_ui/                    páginas estáticas
│   └── outbound/                      quem o sistema CHAMA
│       ├── persistence_postgres/      models SQLAlchemy, repositórios, UoW        [de infrastructure/]
│       ├── notification_smtp/         envio de e-mail (NOVO)
│       └── security/                  JWT e bcrypt
├── bootstrap/                         composição (injeta adapters nas portas) + config + main do app
tests/
├── unit/        núcleo com portas outbound falsas
├── integration/ adapters outbound reais (Postgres, SMTP de teste)
└── architecture/ verifica que core não importa adapters
```

### E.4 Como os novos itens se encaixam

| Item | Porta | Adaptador |
| :-- | :-- | :-- |
| Abrir OS composta | `ports/inbound/abrir_os.py` | `adapters/inbound/http_rest/routers/ordens_servico.py` |
| Listagem priorizada | `ports/inbound/listar_os.py` + `ports/outbound/.../ordem_servico_repository.py` | rota HTTP; `persistence_postgres` aplica o `ORDER BY` por prioridade |
| Webhook de aprovação | reusa `ports/inbound/decidir_orcamento.py` | `adapters/inbound/http_webhook/` (valida assinatura, traduz payload) |
| E-mail | `ports/outbound/notificador_de_status.py` | `adapters/outbound/notification_smtp/smtp_notificador.py` |

### E.5 Etapas da refatoração (Hexagonal)

1. Linha de base: suíte verde + cobertura + teste de arquitetura (core não importa `adapters`).
2. **Mover e renomear** pacotes (`domain` → `core/domain`, `infrastructure` → `adapters/outbound`, `presentation` → `adapters/inbound`) com script e ruff para reescrever imports; é um PR grande e mecânico, ideal de fazer cedo e **com todos os outros PRs congelados**.
3. Criar `ports/inbound` (por serviço ou para os casos centrais) e fazer os routers dependerem delas.
4. Consolidar as portas de saída em `ports/outbound`.
5. Implementar os requisitos novos (Parte C) no novo molde.
6. Atualizar guia, estrutura de pastas, C4 (o C4 ganha uma visão de hexágono), CHANGELOG.

**Esforço relativo:** médio-alto (muita movimentação de arquivos e imports; ~60 casos de uso). **Risco de regressão:** médio (mecânico, mas conflita com trabalho em paralelo se não for feito no começo).

---

## F. Comparativo e recomendação

| Critério | Clean Architecture | Arquitetura Hexagonal |
| :-- | :-- | :-- |
| Distância da Fase 1 | **Pequena** – estrutura já é praticamente Clean | Média – exige reorganizar pastas e criar portas de entrada |
| Volume de mudança | Foco em DTOs e fronteira HTTP | Foco em mover/renomear pacotes + portas inbound |
| Conceito principal | Regra de dependência em círculos, casos de uso como núcleo | Núcleo cercado por portas e adaptadores (entrada × saída) |
| Encaixe com os requisitos novos | Bom (e-mail = gateway; webhook = controller) | **Muito bom** (webhook e e-mail são adaptadores naturais, entrada e saída) |
| Risco de conflito entre PRs do grupo | Baixo | Alto no PR de reorganização (mitigável fazendo-o primeiro) |
| Custo de cerimônia | Moderado (DTOs de saída) | Maior (interfaces de entrada) |
| Facilidade de explicar no vídeo/README | Boa – o grupo já tem a documentação em camadas | Boa e visual – o hexágono é um diagrama marcante |
| Risco de ser visto como "só renomeou" | Médio, se não adotar DTOs/controllers | Médio, se as portas de entrada forem decorativas |

**Recomendação:** **Clean Architecture**, na versão "leve" da D.3 (manter as 4 pastas, adicionar `application/dtos`, controllers/presenters, porta de notificação). A Fase 1 já respeita a regra de dependência, então a refatoração aporta valor real (DTOs, fronteiras finas, regra de prioridade no domínio) sem consumir o tempo que a infraestrutura (K8s, Terraform, CD), a parte mais pesada e arriscada da fase, vai exigir. Escolham **Hexagonal** se o grupo quiser a vitrine conceitual maior ou gostar do modelo de portas/adaptadores; nesse caso, façam a reorganização **na primeira semana**, antes de abrir PRs de funcionalidades.

Em ambos os casos, o critério de aceite é o mesmo: teste automatizado de dependência + suíte da Fase 1 verde + documentação atualizada.

---

## G. Decisões que o grupo precisa tomar

| ID | Decisão | Opções | Minha sugestão |
| :-- | :-- | :-- | :-- |
| G-1 | Onde o código da Fase 2 vive | (a) mesmo clone/repo da Fase 1 em branches novas, esta pasta só para docs; (b) mover tudo para esta pasta | (a) – o enunciado exige o **mesmo repositório** |
| G-2 | Nuvem/local para Terraform e CD | AWS, Azure, GCP, só local, misto (C.5) | Misto; decidir pela conta/crédito que o grupo realmente tem |
| G-3 | Contrato de abertura da OS | (a) estender `POST /ordens-servico` com serviços/peças opcionais; (b) nova rota composta | (a), mantendo compatibilidade; definir se a OS já nasce com orçamento calculado |
| G-4 | Ordem e mapeamento de status (9 internos × 6 do enunciado) | ver C.1 | Propor as regras da C.1 ao professor/grupo e documentar |
| G-5 | Leitura de "atualização por e-mail" | saída (notificar cliente) vs entrada (cliente responde) | Saída + webhook para entrada |
| G-6 | Grau de purismo da arquitetura | Clean leve / Clean completa / Hexagonal completa / Hexagonal com poucas portas inbound | Clean leve |
| G-7 | Quais status somem da listagem | só FINALIZADA+ENTREGUE (literal) ou também CANCELADA | Incluir CANCELADA também, e documentar; parâmetro para ver encerradas |
| G-8 | Notificação: pós-commit simples ou outbox | ver C.2 | Pós-commit; outbox só se sobrar tempo |
| G-9 | Provedor de e-mail em nuvem | SES, SendGrid, Gmail (senha de app), apenas Mailpit | Mailpit local + um SMTP real simples para o vídeo |
| G-10 | Divisão do trabalho | tamanho do grupo e responsáveis por trilha | preencher na Parte H (prazo: 19/01/2027) |

---

## H. Fases de execução

> Esforço relativo (P/M/G). Prazo final: **19/01/2027**, cerca de 11 semanas a partir de 04/11/2026. As datas abaixo são sugestões que já descontam o fim de ano (Natal e Ano Novo costumam reduzir o ritmo). A infraestrutura começa cedo porque é o maior risco e corre em paralelo com a refatoração.

| Fase | Janela sugerida | Marco |
| :-- | :-- | :-- |
| 0 – Alinhamento | 04/11 a 10/11 | Arquitetura, nuvem e G-1 a G-10 decididos; repo compartilhado com `soat-architecture` |
| 1 – Linha de base e arquitetura | 11/11 a 24/11 | Reestruturação concluída, testes verdes |
| 3 – Docker e K8s local | 16/11 a 10/12 | HPA escalando em cluster local |
| 2 – APIs | 25/11 a 19/12 | Todos os endpoints do PDF com testes |
| 4 – Terraform | 23/11 a 23/12 | Ambiente criado do zero por Terraform |
| 5 – CI/CD | 14/12 a 06/01 | Push na `main` implanta no cluster |
| 6 – Documentação e evidências | 28/12 a 12/01 | README, desenho e collection prontos |
| **Congelamento de código** | **09/01** | Só correções a partir daqui |
| 7 – Vídeo e entrega | 11/01 a 17/01 | Vídeo publicado e PDF montado |
| Buffer | 18/01 a 19/01 | Conferir acesso do `soat-architecture` e submeter |

Como a conta de nuvem pode levar dias para liberar, a decisão G-2 deve sair até 10/11. A gravação do vídeo precisa do ambiente estável, então o congelamento em 09/01 protege a Fase 7.

### Fase 0 – Alinhamento (P)
- Escolher a arquitetura (D ou E) e fechar G-1 a G-10.
- Criar branch/épico "Fase 2" e as issues (uma por item das fases abaixo), seguindo o fluxo do `AGENTS.md`.
- Compartilhar o repositório com o usuário **`soat-architecture`** (já, para não esquecer).
- Confirmar conta de nuvem e créditos.

### Fase 1 – Linha de base e arquitetura (M; Clean) / (G; Hexagonal)
- Rodar a suíte, medir cobertura, criar o teste da regra de dependência.
- Aplicar a reestruturação escolhida (D.5 ou E.5).
- **Meta:** testes verdes, estrutura nova documentada, nenhuma funcionalidade nova ainda.

### Fase 2 – Funcionalidades de API (G) – *em paralelo com a Fase 3*
- Regra de prioridade e nova listagem (+ paginação) e atualização do RF-14.
- Abertura de OS composta.
- Consulta de status (ajustes/documentação).
- Webhook de aprovação (autenticação, idempotência).
- Notificação por e-mail (porta, adaptador, handler, Mailpit).
- **Meta:** todos os endpoints do PDF funcionando com testes.

### Fase 3 – Containerização e Kubernetes (M) – *em paralelo com a Fase 2*
- Revisar Dockerfile/compose (+ Mailpit); separar migration.
- Escrever `/k8s` (base + overlays), HPA, Job de migration, probes, requests/limits.
- Validar no cluster **local** (kind/minikube) com metrics-server; rodar o Locust e ver o HPA escalar.
- **Meta:** `kubectl apply -k` sobe tudo localmente e o HPA reage à carga.

### Fase 4 – Terraform (G)
- Módulos para cluster + banco (+ registry) conforme G-2; variáveis, outputs, `README` de `/infra`.
- `terraform validate/plan` no CI; `apply` controlado.
- **Meta:** ambiente criado do zero por Terraform e destruível.

### Fase 5 – CI/CD (M)
- Estender o `ci.yml`: push da imagem, deploy, Job de migration, `kubectl apply`, rollout status, smoke test.
- GitHub Secrets/Environments; sem segredo no repo.
- **Meta:** um push na `main` implanta no cluster sem passo manual.

### Fase 6 – Documentação e evidências (M)
- README da Fase 2 (arquitetura, execução local, K8s, Terraform, collection, vídeo).
- Desenho da arquitetura (Mermaid + imagem para o PDF do portal).
- Atualizar `docs/` e CHANGELOG; coletar evidências (cobertura, HPA, pipeline verde).

### Fase 7 – Vídeo e entrega (P/M)
- Ensaiar e gravar (≤ 15 min), publicar (não listado), colocar o link no README.
- Montar o **PDF do portal** (link do repo, desenho da arquitetura, link do vídeo).
- Conferir acesso do `soat-architecture` ao repositório; **buffer de pelo menos 1 dia** antes do prazo.

### Divisão sugerida (ajustar ao tamanho do grupo)

| Trilha | Conteúdo | Fases |
| :-- | :-- | :-- |
| Aplicação | Refatoração + APIs + e-mail + testes | 1, 2 |
| Plataforma | Docker, K8s, HPA | 3 |
| Nuvem/IaC | Terraform + CD | 4, 5 |
| Documentação/entrega | README, desenho, vídeo, PDF | 6, 7 (todos colaboram) |

---

## I. Riscos

| Risco | Impacto | Mitigação |
| :-- | :-- | :-- |
| Conta de nuvem restringe EKS/IAM ou créditos acabam | CD e Terraform inviáveis | Decidir G-2 logo; ter o overlay local funcionando como plano B; `terraform destroy` após gravar |
| HPA não escala (sem metrics-server / sem requests) | Perde o item mais visual da demo | Testar na Fase 3; Locust já existe |
| Migration concorrente com várias réplicas | Falha de deploy | Job único antes do rollout (B.3) |
| Mudar RF-14 quebra testes da Fase 1 | Regressão | Atualizar RF + testes no mesmo PR; documentar no CHANGELOG |
| Refatoração grande conflita com PRs paralelos | Retrabalho | Fazer o PR estrutural primeiro e congelar merges durante ele |
| E-mail dentro da transação | Falha de SMTP desfaz a OS / lentidão | Pós-commit (C.2) |
| Segredos vazando no git ou nos logs do CI | Incidente e perda de nota | Secrets do GitHub, `gitleaks` já existente, `secret.example.yaml` |
| Vídeo passando de 15 min | Descumprimento | Roteiro cronometrado; ensaiar |
| Escopo de e-mail mal interpretado | Retrabalho | Validar G-5 com o professor |
| Rate limit por pod | Limite efetivo × N réplicas | Documentar; Redis só se sobrar tempo |

---

## J. Checklist final de entrega

**Código e arquitetura**
- [ ] Arquitetura escolhida aplicada e documentada; teste de dependência passando
- [ ] Clean Code revisado nos arquivos tocados
- [ ] Suíte da Fase 1 + novos testes verdes; cobertura ≥ 80%

**APIs**
- [ ] Abertura de OS (cliente, veículo, serviços, peças) devolve ID único
- [ ] Consulta de status
- [ ] Webhook de aprovação/recusa (autenticado, idempotente)
- [ ] Listagem: ordem por status, antigas primeiro, sem finalizadas/entregues
- [ ] Atualização de status por e-mail funcionando

**Infraestrutura**
- [ ] Dockerfile e docker-compose revisados
- [ ] `/k8s`: Deployments, Services, ConfigMaps, Secrets, HPA
- [ ] `/infra`: Terraform do cluster e do banco + README
- [ ] Pipeline: build, testes, build da imagem, deploy no cluster, deploy do banco, aplicação dos manifestos

**Documentação e portal**
- [ ] README com solução, desenho (componentes, infra, fluxo de deploy), instruções local/K8s/Terraform
- [ ] Link da collection/Swagger
- [ ] Vídeo ≤ 15 min (deploy, CI/CD, APIs, autoescala) publicado
- [ ] Repositório compartilhado com **`soat-architecture`**
- [ ] PDF do portal: link do repo + desenho da arquitetura + link do vídeo
