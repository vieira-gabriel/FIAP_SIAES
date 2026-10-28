# Estrutura de Pastas do Projeto

Este documento descreve a reorganização da estrutura de pastas do repositório para alinhá-la à documentação do projeto (`docs/requisitos-nao-funcionais.md` e `docs/ddd/linguagem-ubiqua.md`), indicando a origem de cada mudança.

---

## 1. Estrutura Atual

```text
src/
├── domain/
│   ├── entities/
│   │   ├── ordem_servico.py
│   │   └── usuario.py
│   ├── value_objects/
│   │   └── perfil_usuario.py
│   ├── events/
│   ├── repositories/
│   │   ├── ordem_servico_repository.py
│   │   └── usuario_repository.py
│   └── exceptions.py
├── application/
│   ├── use_cases/
│   │   ├── autenticar_usuario.py
│   │   └── criar_os.py
│   ├── ports/
│   │   ├── password_hasher.py
│   │   └── token_service.py
│   ├── events/
│   └── handlers/
├── infrastructure/
│   ├── database/
│   ├── repositories/
│   │   ├── postgres_ordem_servico_repository.py
│   │   └── postgres_usuario_repository.py
│   └── security/
│       ├── bcrypt_password_hasher.py
│       └── jwt_token_service.py
└── presentation/
    ├── main.py
    ├── routers/
    │   └── autenticacao.py
    ├── schemas/
    │   └── autenticacao.py
    └── middlewares/
        └── dependencies.py
tests/
├── unit/
└── integration/
docs/
└── security/
```

---

## 2. Arquivos Movidos ou Renomeados

| Caminho Anterior | Caminho Novo | Origem na Documentação |
| :--- | :--- | :--- |
| `src/domain/ordem_servico.py` | `src/domain/entities/ordem_servico.py` | Linguagem Ubíqua §4 — Entidade / Raiz de Agregado |
| `src/application/criar_ordem_servico.py` | `src/application/use_cases/criar_os.py` | Linguagem Ubíqua §4 — Caso de Uso (Command Handler) |
| `src/infrastructure/ordem_servico_repository.py` | `src/infrastructure/repositories/postgres_ordem_servico_repository.py` | Linguagem Ubíqua §4 — Adaptador de Infraestrutura; RNF-09 (PostgreSQL) |
| `src/api/schemas.py` | `src/presentation/schemas.py` | RNF-01 — camada `presentation`; RNF-16 — DTOs de entrada e saída |
| `src/presentation/schemas.py` | `src/presentation/schemas/` (pasta, um arquivo por recurso) | Decisão do grupo no fechamento da Fase 0 (guia de desenvolvimento, seção 8.1) |
| `tests/test_ordem_servico.py` | `tests/unit/test_ordem_servico.py` | RNF-12 — testes unitários para entidades e objetos de valor |

A pasta `src/api/` foi removida, pois a RNF-01 nomeia a camada de entrada como `presentation`.

---

## 3. Pastas e Arquivos Criados

| Caminho | Origem na Documentação |
| :--- | :--- |
| `src/domain/value_objects/` | Linguagem Ubíqua §2 (CPF, CNPJ, Placa, Valor, StatusOS) e §4 — Objeto de Valor (`src/domain/value_objects/cpf.py` e `src/domain/value_objects/cnpj.py`, classes separadas por decisão do grupo na issue #14) |
| `src/domain/repositories/ordem_servico_repository.py` | Linguagem Ubíqua §4 — Porta de Repositório (Interface Abstrata); RNF-02 — isolamento do domínio |
| `tests/integration/` | RNF-13 — testes de integração dos fluxos principais |
| `src/presentation/routers/` | Decisão do grupo no fechamento da Fase 0: rotas FastAPI, um arquivo por recurso |
| `src/domain/events/`, `src/application/events/`, `src/application/handlers/` e `src/infrastructure/database/` | Seção 6 do modelo C4, aprovadas pelo grupo na issue #9 |
| `src/presentation/middlewares/` | Seção 6 do modelo C4, aprovada pelo grupo na issue #9; substitui `src/presentation/auth/` |
| `docs/security/` | RNF-07 — relatório de análise de vulnerabilidades |

A porta do repositório no domínio é o que permite à camada `application` depender de uma abstração, e não da implementação em PostgreSQL, conforme exige a RNF-02.

---

## 4. Decisões que Não Constam na Documentação

| Item | Justificativa |
| :--- | :--- |
| Arquivos `__init__.py` em cada pasta de `src/` | A Linguagem Ubíqua referencia classes como módulos Python (ex.: `domain.entities.OrdemServico`), o que pressupõe pacotes. Também garantem que as pastas sejam versionadas pelo Git. |
| Arquivo `.gitkeep` em `docs/security/` | O Git não versiona pastas vazias; o arquivo pode ser removido quando a pasta receber o relatório da análise de vulnerabilidades (RNF-07). O de `tests/integration/` já foi removido, pois a pasta tem testes. |

---

## 5. Autenticação com JWT (RNF-03)

A documentação exige autenticação JWT (RNF-03) e proíbe senhas e segredos em texto plano (RNF-06), mas não define onde o código fica. A distribuição abaixo segue as mesmas camadas do restante do projeto e mantém o domínio livre de bibliotecas de JWT e de hashing (RNF-02).

| Camada | Arquivo | Responsabilidade |
| :--- | :--- | :--- |
| Domínio | `src/domain/entities/usuario.py` | Entidade `Usuario` com o perfil de acesso: Atendente, Mecânico ou Gerente (Linguagem Ubíqua §3). |
| Domínio | `src/domain/repositories/usuario_repository.py` | Porta (ABC) para buscar usuários, no mesmo padrão da porta de Ordem de Serviço. |
| Aplicação | `src/application/ports/token_service.py` | Interface para emitir e validar tokens. |
| Aplicação | `src/application/ports/password_hasher.py` | Interface para gerar e verificar o hash de senhas (RNF-06). |
| Aplicação | `src/application/use_cases/autenticar_usuario.py` | Caso de uso de login: verifica as credenciais e devolve o token. |
| Infraestrutura | `src/infrastructure/security/jwt_token_service.py` | Implementação de `token_service` com uma biblioteca de JWT. |
| Infraestrutura | `src/infrastructure/security/bcrypt_password_hasher.py` | Implementação de `password_hasher` com bcrypt. |
| Infraestrutura | `src/infrastructure/repositories/postgres_usuario_repository.py` | Implementação da porta de usuário em PostgreSQL. |
| Apresentação | `src/presentation/middlewares/dependencies.py` | Validação do token nas rotas administrativas e operacionais e checagem do perfil exigido. |

Pontos de atenção:

* **Rotas públicas:** a consulta de status da OS (RF-25) e a aprovação ou rejeição do orçamento (RF-26) ficam fora da autenticação, conforme a RNF-03. O cliente não é um `Usuario` do sistema; ele se identifica pelo número da OS junto com o CPF/CNPJ do titular. Perfil sem permissão recebe `403` (RF-02).
* **Chave secreta:** a chave de assinatura do JWT deve vir de variável de ambiente e nunca ser commitada (RNF-06).
* **Pasta `application/ports/`:** é uma decisão nova, que não consta na documentação. Hashing e emissão de token não são conceitos do negócio, por isso as interfaces ficam na aplicação, e não em `domain/`.

---

## 6. Itens da Documentação Ainda Não Representados

A pasta `migrations/` do Alembic (guia, seção 8.1) fica na raiz do projeto, junto com o `alembic.ini`, e foi criada na issue #25 com a revisão de base `0001_schema_base`, vazia; as tabelas entram com cada entidade. `src/infrastructure/config.py` (configuração) e `src/presentation/container.py` (montagem das dependências), decididos na issue #9, foram criados na issue #22; o container monta a engine, a fábrica de sessões, os serviços de token e de hash e o verificador do banco (issue #26). O login já está ligado: o container oferece `obter_autenticar_usuario` e executa a carga inicial de usuários na subida; as demais funções `obter_<caso_de_uso>` entram com os casos de uso seguintes.

A autenticação JWT (seção 5), a configuração do PostgreSQL (RNF-08) e o `Dockerfile` com o `docker-compose.yml` (RNF-15) já estão implementados. Permanecem pendentes, por dependerem de implementação:

* a porta `ordem_servico_repository.py` e o caso de uso `criar_os.py`, que existem vazios (issues #46 e Fase 5);
* os adaptadores PostgreSQL da OS, do estoque, do cliente e do veículo, com os modelos do ORM e as tabelas (Fase 4);
* os eventos de domínio da OS e os handlers de `application/handlers/` (issue #45);
* o relatório da análise de vulnerabilidades em `docs/security/` (RNF-07) e a evidência da medição de cobertura (RNF-14), que a Fase 7 registra.
