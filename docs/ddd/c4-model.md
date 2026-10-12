# Documentação de Arquitetura de Software - Modelo C4

> **Projeto:** Sistema de Gestão de Oficina Mecânica (Tech Challenge - Fase 1)  
> **Linguagem & Framework:** Python 3.12 / FastAPI / Uvicorn  
> **Banco de Dados:** PostgreSQL 16  
> **Padrão Arquitetural:** Monólito em Camadas (Layered Monolith) inspirado em Domain-Driven Design (DDD) e Clean Architecture  

---

## 1. Visão Geral do Modelo C4

O **Modelo C4** (criado por Simon Brown) é uma abordagem hierárquica e incremental para documentar a arquitetura de software em quatro níveis de abstração: **Contexto**, **Contêineres**, **Componentes** e **Código**. Esta estrutura permite comunicar a arquitetura de forma clara tanto para partes interessadas do negócio quanto para o time técnico de desenvolvimento.

```
Nível 1: Contexto (System Context) ---> Visão geral das pessoas e sistemas
Nível 2: Contêineres (Containers)  ---> Visão das aplicações e bancos de dados executáveis
Nível 3: Componentes (Components)  ---> Visão dos módulos internos da aplicação Python (src/api, application, domain, infrastructure)
Nível 4: Código (Code)             ---> Visão detalhada das classes de domínio, VOs e agregados
```

---

## 2. Nível 1: Diagrama de Contexto (System Context)

O Diagrama de Contexto apresenta o sistema como uma caixa-preta central, mapeando todas as personas e papéis que com ele interagem, divididos nas duas frentes da solução: **Frente da Loja** (acesso autenticado via RBAC) e **Frente do Cliente** (acompanhamento público desautenticado).

### Diagrama de Contexto (Mermaid)

```mermaid
flowchart TD
    subgraph ATORES_LOJA ["🏢 Frente da Loja (Interno - JWT / RBAC)"]
        Atendente["👤 Atendente\n[Pessoa]\nRealiza cadastro de clientes, veículos,\nabertura de OS e entrega de veículos."]
        Mecanico["👤 Mecânico\n[Pessoa]\nRealiza diagnósticos, insere itens/peças,\ncalcula orçamentos e executa serviços."]
        Gerente["👤 Gerente / Admin\n[Pessoa]\nAdministrador com acesso total (CRUD),\nrelatórios e gestão do catálogo/estoque."]
    end

    subgraph SISTEMA ["⚙️ Fronteira do Sistema"]
        OficinaSystem["🚘 Sistema de Gestão de Oficina Mecânica\n[Software System]\nGerencia o ciclo de vida completo de Ordens de Serviço,\ncontrole atômico de estoque, cadastros e acompanhamento público."]
    end

    subgraph ATORES_CLIENTE ["📲 Frente do Cliente (Externo - Público)"]
        Cliente["👤 Cliente\n[Pessoa]\nConsulta o status da OS em tempo real\ne aprova ou rejeita orçamentos propostos."]
    end

    Atendente -->|"Cadastra clientes/veículos e abre OS\n[HTTPS / REST API / JWT (Role: Atendente)]"| OficinaSystem
    Mecanico -->|"Insere diagnósticos, peças e executa OS\n[HTTPS / REST API / JWT (Role: Mecanico)]"| OficinaSystem
    Gerente -->|"Administra sistema, estoque e relatórios\n[HTTPS / REST API / JWT (Role: Gerente)]"| OficinaSystem
    Cliente -->|"Consulta status da OS (Nº OS + CPF/CNPJ)\ne aprova/rejeita orçamento [HTTPS / REST API Pública]"| OficinaSystem
```

### Relação de Atores e Escopo de Acesso

| Ator | Tipo de Acesso | Interface / Protocolo | Escopo Principal de Atuação |
| :--- | :--- | :--- | :--- |
| **Atendente** | Autenticado (JWT - `Atendente`) | API REST (HTTPS) | Abertura de OS, cadastro/vínculo de cliente e veículo, listagem de catálogo e entrega do veículo. |
| **Mecânico** | Autenticado (JWT - `Mecanico`) | API REST (HTTPS) | Diagnóstico técnico, inclusão de serviços/peças, cálculo de orçamento e execução da manutenção. |
| **Gerente (Admin)** | Autenticado (JWT - `Gerente`) | API REST (HTTPS) | Acesso total administrativo (CRUD amplo), forçar alterações de status, cancelamentos e métricas de SLA. |
| **Cliente** | Público (Sem JWT) | API REST (HTTPS) | Consulta de status em tempo real (Nº OS + CPF/CNPJ/Placa), visualização do orçamento e aprovação/rejeição. |

---

## 3. Nível 2: Diagrama de Contêineres (Container Diagram)

O Diagrama de Contêineres detalha as unidades de implantação executáveis (contêineres Docker) que compõem a arquitetura do monólito, seus protocolos de comunicação e escolhas de tecnologia.

### Diagrama de Contêineres (Mermaid)

```mermaid
flowchart TD
    subgraph CLIENTES ["🌐 Camada de Entrada / Clientes HTTP"]
        BrowserLoja["💻 Portal da Loja / Swagger UI\n[Web Browser / OpenAPI]\nInterface interativa para atendimento e mecânicos."]
        BrowserCliente["📱 Portal / App do Cliente\n[Web Browser / Mobile]\nAcompanhamento público e aprovação de orçamento."]
    end

    subgraph DOCKER_COMPOSE ["🐳 Docker Compose Environment"]
        subgraph BACKEND_CONTAINER ["Contêiner: app (Python 3.12)"]
            FastAPIApp["⚡ API Back-end Monolítica\n[Container: Python / FastAPI / Uvicorn]\nProcessa regras de negócio, autenticação JWT,\nRBAC, máquina de estados da OS e APIs REST."]
        end

        subgraph DATABASE_CONTAINER ["Contêiner: db (PostgreSQL 16)"]
            PostgresDB[("🐘 Banco de Dados Relacional\n[Container: PostgreSQL 16]\nPersistência transacional ACID de clientes, veículos,\nserviços, estoque de peças e histórico de OSs.")]
        end
    end

    BrowserLoja -->|"Chamadas de API Autenticadas\n[JSON / HTTPS / Bearer JWT]"| FastAPIApp
    BrowserCliente -->|"Consultas Públicas e Aprovação\n[JSON / HTTPS / Rate-Limited]"| FastAPIApp
    FastAPIApp -->|"Persistência e Leitura Transacional\n[SQL / TCP Port 5432 / SQLAlchemy ORM]"| PostgresDB
```

### Detalhamento dos Contêineres

| Contêiner | Tecnologia | Função e Responsabilidade | Protocolos & Portas |
| :--- | :--- | :--- | :--- |
| **API Back-end (`app`)** | Python 3.12, FastAPI, Uvicorn | Expor endpoints RESTful, validar tokens JWT e permissões RBAC, executar casos de uso, orquestrar a máquina de estados da OS e sanitizar dados de entrada. | HTTP/JSON (Porta 8000) |
| **Banco de Dados (`db`)** | PostgreSQL 16 | Armazenamento relacional persistente com suporte a transações ACID, garantindo integridade referencial e baixa atômica de estoque. | SQL/TCP (Porta 5432) |
| **Orquestrador Local** | Docker Compose v2 | Orquestra e inicializa os contêineres `app` e `db` em rede isolada para execução local determinística. | Docker Network |

---

## 4. Nível 3: Diagrama de Componentes (Component Diagram)

O Diagrama de Componentes descreve a organização interna do contêiner da aplicação Python, evidenciando o desacoplamento das camadas da **Clean / Layered Architecture** com a entrada centralizada em `src/api/`.

### Diagrama de Componentes (Mermaid)

```mermaid
flowchart TD
    subgraph API_LAYER ["1. Camada de API / Entrada (src/api/)"]
        AuthController["🔐 AuthController\nEndpoints de login e geração de JWT."]
        OSController["🛠️ OrdemServicoController\nEndpoints administrativos de OS (Criar, Listar, Transicionar)."]
        ClienteController["👤 ClienteController\nEndpoints de CRUD de Clientes e Veículos."]
        EstoqueController["📦 EstoqueController\nEndpoints de gestão e entrada de estoque de peças."]
        PublicController["📲 AcompanhamentoPublicoController\nEndpoint desautenticado de consulta por CPF/OS."]
        
        AuthGuard["🛡️ RBACGuard / JWT Middleware\nValida token Bearer e claim 'role' (Atendente, Mecanico, Gerente)."]
        RateLimiter["⚡ RateLimitingMiddleware\nProtege rotas públicas contra força bruta DoS."]
    end

    subgraph APPLICATION ["2. Camada de Aplicação (src/application/)"]
        CriarOSUseCase["⚙️ CriarOrdemServicoUseCase"]
        IniciardiagnosticoUseCase["⚙️ IniciarDiagnosticoUseCase"]
        CalcularOrcamentoUseCase["⚙️ CalcularOrcamentoUseCase"]
        AprovarOrcamentoUseCase["⚙️ AprovarOrcamentoUseCase"]
        ConsultarStatusPublicoUseCase["⚙️ ConsultarStatusPublicoUseCase"]
        
        Ports["🔌 Ports (Interfaces de Serviço)\nITokenProvider, IPasswordHasher"]
        EventDispatcher["⚡ EventDispatcher (In-Memory)\nBarramento síncrono para eventos de domínio."]
        EstoqueHandler["📦 BaixaEstoqueHandler\nEscuta OrcamentoAprovado e efetua baixa."]
    end

    subgraph DOMAIN ["3. Camada de Domínio (src/domain/ - Pure Python Dataclasses)"]
        AggOS[("🟩 Agregado: OrdemServico\nEntidade-raiz com regras da máquina de estados.")]
        AggEstoque[("🟩 Agregado: EstoquePeca\nEntidade com controle quantitativo.")]
        Entities["👤 Entidades\nCliente, Veiculo, Usuario."]
        VOs["💎 Value Objects\nCpfCnpj, Placa, StatusOS, PerfilUsuario."]
        DomainEvents["🟧 Eventos de Domínio\nOrcamentoAprovadoEvent, StatusOSAlteradoEvent."]
        IRepositories["🔌 Interfaces de Repositório (ABCs)\nIOrdemServicoRepository, IEstoqueRepository, IUsuarioRepository."]
    end

    subgraph INFRASTRUCTURE ["4. Camada de Infraestrutura (src/infrastructure/)"]
        PgOSRepo["🐘 PostgresOrdemServicoRepository\nImplementação concreta SQLAlchemy."]
        PgEstoqueRepo["🐘 PostgresEstoqueRepository\nImplementação concreta SQLAlchemy com Lock."]
        JWTProvider["🔐 PyJWTProvider\nImplementação de ITokenProvider."]
        BcryptHasher["🔐 BcryptPasswordHasher\nImplementação de IPasswordHasher."]
        PgDatabase["🐘 SQLAlchemy Session / Postgres Driver"]
    end

    AuthGuard --> AuthController
    RateLimiter --> PublicController
    
    OSController --> CriarOSUseCase
    OSController --> IniciardiagnosticoUseCase
    OSController --> CalcularOrcamentoUseCase
    PublicController --> AprovarOrcamentoUseCase
    PublicController --> ConsultarStatusPublicoUseCase
    
    AprovarOrcamentoUseCase --> AggOS
    AprovarOrcamentoUseCase --> EventDispatcher
    EventDispatcher -->|OrcamentoAprovadoEvent| EstoqueHandler
    EstoqueHandler --> PgEstoqueRepo
    
    CriarOSUseCase --> IRepositories
    AprovarOrcamentoUseCase --> IRepositories
    
    JWTProvider -.->|Implementa| Ports
    BcryptHasher -.->|Implementa| Ports
    PgOSRepo -.->|Implementa| IRepositories
    PgEstoqueRepo -.->|Implementa| IRepositories
    PgOSRepo --> PgDatabase
    PgEstoqueRepo --> PgDatabase
```

---

## 5. Nível 4: Diagrama de Código (Code Diagram)

O Diagrama de Código ilustra a estrutura interna das entidades de domínio (`OrdemServico`, `Cliente`, `Veiculo`, `Usuario`), Objetos de Valor (`CpfCnpj`, `Placa`, `StatusOS`, `PerfilUsuario`) e Eventos, implementados como **`dataclasses` puras do Python** sem acoplamento com frameworks.

### Diagrama de Classes do Domínio (Mermaid / UML)

```mermaid
classDiagram
    class Cliente {
        +UUID id
        +str nome
        +CpfCnpj documento
        +str email
        +str telefone
    }

    class Veiculo {
        +UUID id
        +UUID cliente_id
        +Placa placa
        +str marca
        +str modelo
        +int ano
    }

    class Usuario {
        +UUID id
        +str nome
        +str email
        +str senha_hash
        +PerfilUsuario perfil
        +bool ativo
    }

    class PerfilUsuario {
        <<enumeration>>
        ATENDENTE
        MECANICO
        GERENTE
    }

    class StatusOS {
        <<enumeration>>
        RECEBIDA
        EM_DIAGNOSTICO
        AGUARDANDO_APROVACAO
        EM_EXECUCAO
        FINALIZADA
        ENTREGUE
        CANCELADA
    }

    class OrdemServico {
        +UUID id
        +UUID cliente_id
        +UUID veiculo_id
        +UUID atendente_id
        +Optional~UUID~ mecanico_id
        +StatusOS status
        +List~ItemServico~ servicos
        +List~ItemPeca~ pecas
        +datetime data_abertura
        +Optional~datetime~ data_inicio_execucao
        +Optional~datetime~ data_finalizacao
        +List~DomainEvent~ _domain_events
        +atribuir_mecanico(mecanico_id: UUID) void
        +finalizar_orcamento() void
        +aprovar_orcamento() void
        +rejeitar_orcamento() void
        +concluir_manutencao() void
        +entregar_veiculo() void
        +forcar_cancelamento(motivo: str) void
        +collect_domain_events() List~DomainEvent~
    }

    class ItemServico {
        +UUID servico_id
        +str nome
        +float preco_congelado
    }

    class ItemPeca {
        +UUID peca_id
        +str nome
        +int quantidade
        +float preco_unitario_congelado
        +valor_total() float
    }

    class CpfCnpj {
        <<Value Object>>
        +str valor
        +validar() bool
    }

    class Placa {
        <<Value Object>>
        +str valor
        +eh_mercosul() bool
    }

    class DomainEvent {
        <<interface>>
        +str event_id
        +datetime occurred_on
    }

    class OrcamentoAprovadoEvent {
        +UUID os_id
        +UUID cliente_id
        +List~dict~ itens_pecas
    }

    Usuario "1" --> "1" PerfilUsuario : possui
    Veiculo "*" --> "1" Cliente : pertence a (cliente_id)
    OrdemServico "*" --> "1" Cliente : referencia (cliente_id)
    OrdemServico "*" --> "1" Veiculo : referencia (veiculo_id)
    OrdemServico "*" --> "1" Usuario : atendente (atendente_id)
    OrdemServico "*" --> "0..1" Usuario : mecanico (mecanico_id)
    OrdemServico "1" *-- "*" ItemServico : contem
    OrdemServico "1" *-- "*" ItemPeca : contem
    OrdemServico --> StatusOS : possui estado
    DomainEvent <|-- OrcamentoAprovadoEvent : herda de
    OrdemServico *-- DomainEvent : acumula eventos
```

---

## 6. Rastreabilidade da Arquitetura com a Estrutura de Pastas no Código

A estrutura física do repositório reflete exatamente o desacoplamento proposto pelo C4 Model e pelo DDD:

```text
src/
├── presentation/                  # Nível 3 (Camada de Entrada, Controllers HTTP & Middlewares)
│   ├── controllers/               # Route Handlers FastAPI (Auth, OS, Cliente, Estoque)
│   ├── middlewares/               # JWT Auth & Rate Limiting Guards (Depends / Security)
│   └── schemas/                   # Pydantic DTOs (Validação de Entrada/Saída HTTP)
├── application/                   # Nível 3 (Camada de Aplicação & Casos de Uso)
│   ├── use_cases/                 # Serviços de Orquestração (CriarOS, AprovarOrcamento, Login)
│   ├── ports/                     # Interfaces Abstratas de Serviços (ITokenProvider, IPasswordHasher)
│   ├── events/                    # Event Dispatcher In-Memory
│   └── handlers/                  # Event Handlers (BaixaEstoqueHandler)
├── domain/                        # Nível 4 (Núcleo Puro de Negócio em Python Dataclasses)
│   ├── entities/                  # Dataclasses de Agregados e Entidades (OrdemServico, Cliente, Veiculo, Usuario)
│   ├── value_objects/             # VOs Imutáveis (CpfCnpj, Placa, StatusOS, PerfilUsuario)
│   ├── events/                    # Definição dos Eventos de Domínio (OrcamentoAprovadoEvent)
│   └── repositories/              # Interfaces Abstratas dos Repositórios (ABCs)
└── infrastructure/                # Nível 3 (Adaptadores I/O & Infraestrutura)
    ├── database/                  # Engine SQLAlchemy, Configurações e Sessions
    ├── repositories/              # Implementações Concretas com SQLAlchemy (Postgres)
    └── security/                  # Implementações Concretas de Segurança (PyJWT, Passlib/Bcrypt)
```
