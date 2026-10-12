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
    └── schemas.py
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
| `src/infrastructure/ordem_servico_repository.py` | `src/infrastructure/repositories/postgres_ordem_servico_repository.py` | Linguagem Ubíqua §4 — Adaptador de Infraestrutura; RNF-06 (PostgreSQL) |
| `src/api/schemas.py` | `src/presentation/schemas.py` | RNF-01 — camada `presentation`; RNF-11 — DTOs de entrada e saída |
| `tests/test_ordem_servico.py` | `tests/unit/test_ordem_servico.py` | RNF-09 — testes unitários para entidades e objetos de valor |

A pasta `src/api/` foi removida, pois a RNF-01 nomeia a camada de entrada como `presentation`.

---

## 3. Pastas e Arquivos Criados

| Caminho | Origem na Documentação |
| :--- | :--- |
| `src/domain/value_objects/` | Linguagem Ubíqua §2 (CPF, CNPJ, Placa, Valor, StatusOS) e §4 — Objeto de Valor (`src/domain/value_objects/cpf_cnpj.py`) |
| `src/domain/repositories/ordem_servico_repository.py` | Linguagem Ubíqua §4 — Porta de Repositório (Interface Abstrata); RNF-02 — isolamento do domínio |
| `tests/integration/` | RNF-09 — testes de integração dos fluxos dos casos de uso |
| `docs/security/` | RNF-05 — relatório de análise de vulnerabilidades |

A porta do repositório no domínio é o que permite à camada `application` depender de uma abstração, e não da implementação em PostgreSQL, conforme exige a RNF-02.

---

## 4. Decisões que Não Constam na Documentação

| Item | Justificativa |
| :--- | :--- |
| Arquivos `__init__.py` em cada pasta de `src/` | A Linguagem Ubíqua referencia classes como módulos Python (ex.: `domain.entities.OrdemServico`), o que pressupõe pacotes. Também garantem que as pastas sejam versionadas pelo Git. |
| Arquivos `.gitkeep` em `tests/integration/` e `docs/security/` | O Git não versiona pastas vazias; os arquivos podem ser removidos quando as pastas receberem conteúdo. |

---

## 5. Itens da Documentação Ainda Não Representados

As classes abaixo são citadas na Linguagem Ubíqua, mas a documentação não define o arquivo de cada uma; por isso, ainda não foram criados arquivos para elas:

* **Entidades** (`src/domain/entities/`): `Cliente`, `Veiculo`, `Servico`, `Peca`.
* **Objetos de Valor** (`src/domain/value_objects/`): `CPF`, `CNPJ`, `Placa`, `Valor`, `StatusOS`, `Orcamento`.

Também permanecem pendentes, por dependerem de implementação: autenticação JWT (RNF-03), configuração do PostgreSQL (RNF-06), conteúdo do `Dockerfile` e do `docker-compose.yml` (RNF-08) e medição de cobertura de testes (RNF-10).
