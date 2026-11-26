# Requisitos Não Funcionais (RNF) - Sistema de Oficina Mecânica

Este documento especifica os **Requisitos Não Funcionais (RNF)** do MVP do sistema da oficina mecânica, definindo as restrições arquiteturais, padrões de segurança, requisitos de desempenho, transacionalidade de banco de dados, cobertura de testes e critérios para empacotamento e deploy.

> Documento atualizado em 25/11/2026 - Versão 1.2 (Fase 2: RNF-01, RNF-05 e RNF-15 alterados; RNF-17 a RNF-19 novos)

---

## 1. Arquitetura de Software e Design

##### **RNF-01** - Monólito em Camadas (Layered Monolith)
A aplicação deve ser desenvolvida como uma arquitetura monolítica organizada em camadas estritas (`presentation`, `application`, `domain`, `infrastructure`), garantindo o isolamento da lógica de negócio em relação a tecnologias de interface e frameworks.

Na Fase 2, as camadas seguem a Clean Architecture: os casos de uso recebem e devolvem DTOs (`application/dtos/`) e nunca devolvem entidades; a apresentação converte requisições e respostas em controllers e presenters; e a regra de dependência é verificada automaticamente no CI pelo import-linter.

> Alterado na Fase 2. A arquitetura em camadas passa a seguir a Clean Architecture na versão leve, com DTOs de saída e verificação automática das dependências. Decisões em [ADR 0002](adr/0002-clean-architecture-leve.md) e [ADR 0003](adr/0003-verificacao-da-arquitetura-com-import-linter.md).

##### **RNF-02** - Isolamento do Núcleo de Domínio (Pure Python DDD)
O núcleo de domínio (`src/domain/`) deve ser implementado em **Python 3.12 puro (`dataclasses`)**, permanecendo 100% livre de dependências externas de frameworks web (FastAPI, Flask) ou ORMs (SQLAlchemy, Pydantic).

---

## 2. Segurança, Autorização e Proteção de Dados

##### **RNF-03** - Autenticação JWT e Validação de Roles (RBAC)
A segurança das APIs administrativas da loja deve ser garantida via tokens **JSON Web Token (JWT)**. O token deve transportar a *claim* de perfil (`role`), e cada endpoint deve validar se o usuário autenticado possui o papel necessário (`Atendente`, `Mecanico`, `Gerente`).
* **Respostas Padrão de Erro**:
  * Falta de token ou token inválido/expirado: `401 Unauthorized`
  * Token válido sem a permissão exigida: `403 Forbidden`

##### **RNF-04** - Sanitização de Entradas e Prevenção contra Ataques (OWASP Top 10)
A aplicação deve aplicar proteções ativas contra vulnerabilidades comuns de segurança:
* **Prevenção contra SQL Injection**: Uso exclusivo do SQLAlchemy ORM / drivers relacionais com parâmetros bindados (queries parametrizadas).
* **Prevenção contra IDOR e Enumeração**: Os endpoints públicos de consulta e de aprovação/rejeição da OS devem exigir a combinação obrigatória do Número da OS + CPF/CNPJ do titular (RF-25, RF-26).
* **Sanitização de Entradas**: Todos os campos de texto livre (diagnósticos, observações e motivos de cancelamento) devem ser higienizados para prevenir injeção de scripts maliciosos (XSS).

##### **RNF-05** - Proteção contra DoS e Brute Force (Rate Limiting)
As rotas públicas de acompanhamento e de aprovação/rejeição da OS devem possuir **Rate Limiting** para restringir requisições excessivas por IP (máximo de 10 requisições por minuto por IP), mitigando ataques de negação de serviço, tentativas de adivinhar o CPF/CNPJ e raspagem automatizada de dados. A implementação usa a biblioteca SlowAPI com contador em memória, suficiente para a instância única do MVP.

> Alterado na Fase 2. Com várias réplicas no Kubernetes, o contador em memória passa a valer por pod, e o limite efetivo é de 10 requisições por minuto multiplicado pelo número de pods. A limitação é aceita e documentada. Decisão em [ADR 0012](adr/0012-kubernetes-kustomize-e-hpa.md).

##### **RNF-06** - Gestão de Segredos e Ausência de Credenciais no Repositório
Nenhuma credencial, senha, chave de assinatura ou token pode ser versionado no repositório, inclusive no histórico do Git:
* Chave de assinatura do JWT, credenciais do banco e senhas da carga inicial (RF-03) são lidas de variáveis de ambiente.
* O arquivo `.env` é ignorado pelo Git; o repositório contém apenas `.env.example`, com os nomes das variáveis e sem valores reais.
* A aplicação não inicia quando uma variável obrigatória estiver ausente, em vez de usar um valor padrão.

##### **RNF-07** - Análise de Vulnerabilidades
O projeto deve passar por análise de vulnerabilidades das dependências, do código-fonte e da imagem Docker, com correção ou justificativa de cada achado relevante:
* O relatório ou resultado da análise deve ser armazenado em `docs/security/` e apresentado no vídeo de entrega.
* A análise deve ser executada sobre a versão do commit final da entrega.

---

## 3. Persistência e Transacionalidade (PostgreSQL)

##### **RNF-08** - Garantia de Transações ACID no PostgreSQL
As operações críticas que envolvem múltiplas alterações de estado devem ser executadas em **blocos transacionais ACID nativos do PostgreSQL**. Em caso de falha durante a execução, o sistema deve realizar o rollback completo para manter a consistência do banco de dados. São operações críticas, no mínimo:
* Criação da OS com seus itens.
* Conclusão do orçamento com reserva de peças e registro de pendências (RF-17, RF-18).
* Atualização de saldo com alocação às OS pendentes e liberação de OS (RF-12, RF-19).
* Início da execução com baixa das peças (RF-20).
* Rejeição e cancelamento com estorno das reservas (RF-18, RF-23, RF-26).
* Toda transição de status com o respectivo registro no histórico (RF-24).

##### **RNF-09** - Justificativa da Escolha do Banco de Dados Relacional
A escolha do **PostgreSQL 16** fundamenta-se na necessidade de:
1. **Estrutura Relacional Forte**: Vínculos rígidos entre `Cliente` → `Veículo` → `OrdemServico` → `Serviços/Peças`.
2. **Integridade Referencial**: Impedir exclusões acidentais que corrompam o histórico de atendimentos e estoques.
3. **Consistência Atômica**: Prevenir inconsistências em acessos concorrentes ao saldo de peças em estoque.

---

## 4. Desempenho e Disponibilidade

##### **RNF-10** - Desempenho e Tempo de Resposta da API
As APIs RESTful devem responder a 95% das solicitações em tempo inferior a **500 milissegundos** em condições normais de operação local.

##### **RNF-11** - Congelamento de Valores Cotados na OS
O cálculo do orçamento deve criar registros imutáveis na tabela de itens da OS para garantir que alterações futuras de tabela de preços no cadastro de serviços ou peças não afetem orçamentos já gerados.

---

## 5. Qualidade de Código e Testes Automatizados

##### **RNF-12** - Suíte de Testes Unitários de Domínio (`pytest`)
O projeto deve possuir uma suíte de testes unitários automatizados construída com **`pytest`**, focada na validação isolada das regras de negócio do núcleo de domínio (`src/domain/`), incluindo:
* Validações matemáticas dos VOs (`CPF`, `CNPJ`, `Placa`).
* Regras de transição de status da máquina de estados da OS.
* Cálculo do valor total do orçamento.
* Regras de estoque: reserva, pendência, prioridade pela OS mais antiga, baixa e estorno.

##### **RNF-13** - Testes de Integração dos Fluxos Principais
O projeto deve possuir testes de integração em `tests/integration/`, executados contra um banco PostgreSQL de teste e através das rotas HTTP, cobrindo no mínimo:
* O fluxo completo da OS, da abertura à entrega.
* A rejeição do orçamento e o cancelamento pelo Gerente, com estorno das reservas.
* A aprovação com peça pendente e a liberação da OS pela reposição de estoque.
* O acesso sem token (`401`) e com perfil sem permissão (`403`).

##### **RNF-14** - Cobertura Mínima de Código (Code Coverage >= 80%)
A suíte de testes automatizados deve garantir uma cobertura de código (code coverage) **igual ou superior a 80%** nos módulos críticos do domínio e da aplicação, verificada via `pytest-cov`.

---

## 6. Implantação, Containerização e Documentação

##### **RNF-15** - Empacotamento Docker e Docker Compose
O sistema deve ser totalmente empacotado para execução em contêineres Docker, fornecendo:
* **`Dockerfile`**: Build otimizado da aplicação Python 3.12 em multi-stage.
* **`docker-compose.yml`**: Orquestração dos serviços da API (`app`), do banco relacional (`db`), da migration do banco (`migration`) e do servidor de e-mail de testes (`mailpit`), permitindo subir o ambiente completo com um único comando (`docker compose up --build`).
* A imagem executa só a API; a migration do banco roda em um processo separado, executado uma vez antes da API.

> Alterado na Fase 2. A migration sai do comando de subida da API, para não rodar em paralelo em várias réplicas, e o compose ganha os serviços `migration` e `mailpit`. Decisões em [ADR 0008](adr/0008-notificacao-de-status-por-email.md) e [ADR 0012](adr/0012-kubernetes-kustomize-e-hpa.md).

##### **RNF-16** - Documentação Interativa de API (OpenAPI / Swagger)
A API deve disponibilizar documentação interativa em conformidade com a especificação **OpenAPI 3.0 / Swagger UI** no endpoint `/docs`, detalhando schemas de entrada/saída, códigos de status HTTP e headers de autenticação Bearer JWT.

---

## 7. Orquestração, Infraestrutura e Entrega Contínua (Fase 2)

##### **RNF-17** - Orquestração em Kubernetes com Escalabilidade Automática
A aplicação deve rodar em Kubernetes, com os manifestos em `/k8s` (Deployments, Services, ConfigMaps, Secrets e HorizontalPodAutoscaler), aplicáveis a um cluster local e ao cluster na nuvem. Decisões em [ADR 0009](adr/0009-infraestrutura-aws-learner-lab.md) e [ADR 0012](adr/0012-kubernetes-kustomize-e-hpa.md).
* No mínimo 2 réplicas da API, com `requests` e `limits` de CPU e memória e probes de prontidão e de vida em `/health`.
* HPA por CPU (60%) e memória (80%), de 2 a 6 réplicas, com a escala demonstrada sob carga gerada pelo Locust.
* A migration do banco roda uma vez por deploy, em um Job, antes da atualização da API.
* Nenhum segredo real nos manifestos versionados.

##### **RNF-18** - Infraestrutura como Código (Terraform)
O cluster Kubernetes, o banco de dados e o registry da imagem devem ser provisionados por Terraform, com o código em `/infra` e a documentação de recursos, variáveis, custo e comandos em `infra/README.md`. Decisões em [ADR 0009](adr/0009-infraestrutura-aws-learner-lab.md) e [ADR 0010](adr/0010-terraform-state-e-execucao.md).
* O ambiente deve poder ser criado do zero e destruído por completo pelo Terraform.
* O state fica em armazenamento remoto com lock; arquivos de state e de variáveis com segredos não são versionados.

##### **RNF-19** - Integração e Entrega Contínuas (CI/CD)
A pipeline deve executar o build, os testes, a verificação de arquitetura e de segurança e o build da imagem em todo PR, e, na entrega, publicar a imagem, aplicar a migration do banco, aplicar os manifestos no cluster e verificar a saúde da aplicação. Decisão em [ADR 0011](adr/0011-entrega-continua-por-label.md).
* A entrega é disparada pela label `deploy` em um PR mesclado na `main` ou manualmente.
* Os segredos ficam nos GitHub Secrets do environment de deploy e chegam ao cluster como Secret do Kubernetes.
* O deploy só termina com sucesso depois do rollout completo e da resposta positiva de `/health`.
