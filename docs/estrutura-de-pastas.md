# Estrutura de Pastas do Projeto

Este documento descreve a reorganização da estrutura de pastas do repositório para alinhá-la à documentação do projeto (`docs/requisitos-nao-funcionais.md` e `docs/ddd/linguagem-ubiqua.md`), indicando a origem de cada mudança.

---

## 1. Estrutura Atual

```text
src/
├── domain/
│   ├── entities/
│   │   └── ordem_servico.py
│   ├── value_objects/
│   └── repositories/
│       └── ordem_servico_repository.py
├── application/
│   └── use_cases/
│       └── criar_os.py
├── infrastructure/
│   └── repositories/
│       └── postgres_ordem_servico_repository.py
└── presentation/
    ├── routers/
    ├── schemas/
    └── auth/
tests/
├── unit/
│   └── test_ordem_servico.py
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
| `docs/security/` | RNF-07 — relatório de análise de vulnerabilidades |

A porta do repositório no domínio é o que permite à camada `application` depender de uma abstração, e não da implementação em PostgreSQL, conforme exige a RNF-02.

---

## 4. Decisões que Não Constam na Documentação

| Item | Justificativa |
| :--- | :--- |
| Arquivos `__init__.py` em cada pasta de `src/` | A Linguagem Ubíqua referencia classes como módulos Python (ex.: `domain.entities.OrdemServico`), o que pressupõe pacotes. Também garantem que as pastas sejam versionadas pelo Git. |
| Arquivos `.gitkeep` em `tests/integration/` e `docs/security/` | O Git não versiona pastas vazias; os arquivos podem ser removidos quando as pastas receberem conteúdo. |

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
| Apresentação | `src/presentation/auth/dependencies.py` | Validação do token nas rotas administrativas e operacionais e checagem do perfil exigido. |

Pontos de atenção:

* **Rotas públicas:** a consulta de status da OS (RF-25) e a aprovação ou rejeição do orçamento (RF-26) ficam fora da autenticação, conforme a RNF-03. O cliente não é um `Usuario` do sistema; ele se identifica pelo número da OS junto com o CPF/CNPJ do titular. Perfil sem permissão recebe `403` (RF-02).
* **Chave secreta:** a chave de assinatura do JWT deve vir de variável de ambiente e nunca ser commitada (RNF-06).
* **Pasta `application/ports/`:** é uma decisão nova, que não consta na documentação. Hashing e emissão de token não são conceitos do negócio, por isso as interfaces ficam na aplicação, e não em `domain/`.

---

## 6. Itens da Documentação Ainda Não Representados

As classes abaixo são citadas na Linguagem Ubíqua, mas a documentação não define o arquivo de cada uma; por isso, ainda não foram criados arquivos para elas:

* **Entidades** (`src/domain/entities/`): `Cliente`, `Veiculo`, `Servico`, `Peca`.
* **Objetos de Valor** (`src/domain/value_objects/`): `CPF`, `CNPJ`, `Placa`, `Valor`, `StatusOS`, `Orcamento`.

Também permanecem pendentes, por dependerem de implementação: a lógica da autenticação JWT (RNF-03, ver seção 5), configuração do PostgreSQL (RNF-08), conteúdo do `Dockerfile` e do `docker-compose.yml` (RNF-15) e medição de cobertura de testes (RNF-14).
