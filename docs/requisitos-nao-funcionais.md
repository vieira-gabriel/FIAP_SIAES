# Requisitos Não Funcionais (RNF) - Sistema de Oficina Mecânica

Este documento especifica os **Requisitos Não Funcionais (RNF)** do MVP do sistema da oficina mecânica, definindo as restrições arquiteturais, padrões de segurança, requisitos de desempenho, transacionalidade de banco de dados, cobertura de testes e critérios para empacotamento e deploy.

---

## 1. Arquitetura de Software e Design

##### **RNF-01** - Monólito em Camadas (Layered Monolith)
A aplicação deve ser desenvolvida como uma arquitetura monolítica organizada em camadas estritas (`presentation`, `application`, `domain`, `infrastructure`), garantindo o isolamento da lógica de negócio em relação a tecnologias de interface e frameworks.

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
* **Prevenção contra IDOR e Enumeração**: O endpoint público de consulta de OS deve exigir a combinação obrigatória do Número da OS + CPF/CNPJ ou utilizar hashes UUID alfanuméricos públicos.
* **Sanitização de Entradas**: Todos os campos de texto livre (diagnósticos e observações) devem ser higienizados para prevenir injeção de scripts maliciosos (XSS).

##### **RNF-05** - Proteção contra DoS e Brute Force (Rate Limiting)
A API pública de acompanhamento da OS deve possuir middleware de **Rate Limiting** para restringir requisições excessivas por IP (ex.: máximo de 10 requisições por minuto por IP), mitigando ataques de negação de serviço e raspagem automatizada de dados.

---

## 3. Persistência e Transacionalidade (PostgreSQL)

##### **RNF-06** - Garantia de Transações ACID no PostgreSQL
As operações críticas que envolvem múltiplas alterações de estado (como a criação da OS, alteração de status e reserva/baixa de peças) devem ser executadas em **blocos transacionais ACID nativos do PostgreSQL**. Em caso de falha durante a execução, o sistema deve realizar o rollback completo para manter a consistência do banco de dados.

##### **RNF-07** - Justificativa da Escolha do Banco de Dados Relacional
A escolha do **PostgreSQL 16** fundamenta-se na necessidade de:
1. **Estrutura Relacional Forte**: Vínculos rígidos entre `Cliente` → `Veículo` → `OrdemServico` → `Serviços/Peças`.
2. **Integridade Referencial**: Impedir exclusões acidentais que corrompam o histórico de atendimentos e estoques.
3. **Consistência Atômica**: Prevenir inconsistências em acessos concorrentes ao saldo de peças em estoque.

---

## 4. Desempenho e Disponibilidade

##### **RNF-08** - Desempenho e Tempo de Resposta da API
As APIs RESTful devem responder a 95% das solicitações em tempo inferior a **500 milissegundos** em condições normais de operação local.

##### **RNF-09** - Congelamento de Valores Cotados na OS
O cálculo do orçamento deve criar registros imutáveis na tabela de itens da OS para garantir que alterações futuras de tabela de preços no cadastro de serviços ou peças não afetem orçamentos já gerados.

---

## 5. Qualidade de Código e Testes Automatizados

##### **RNF-10** - Suíte de Testes Unitários de Domínio (`pytest`)
O projeto deve possuir uma suíte de testes unitários automatizados construída com **`pytest`**, focada na validação isolada das regras de negócio do núcleo de domínio (`src/domain/`), incluindo:
* Validações matemáticas dos VOs (`CPF`, `CNPJ`, `Placa`).
* Regras de transição de status da máquina de estados da OS.
* Cálculo do valor total do orçamento e lógica de desconto/taxas.

##### **RNF-11** - Cobertura Mínima de Código (Code Coverage >= 80%)
A suíte de testes automatizados deve garantir uma cobertura de código (code coverage) **igual ou superior a 80%** nos módulos críticos do domínio e da aplicação, verificada via `pytest-cov`.

---

## 6. Implantação, Containerização e Documentação

##### **RNF-12** - Empacotamento Docker e Docker Compose
O sistema deve ser totalmente empacotado para execução em contêineres Docker, fornecendo:
* **`Dockerfile`**: Build otimizado da aplicação Python 3.12 em multi-stage.
* **`docker-compose.yml`**: Orquestração dos serviços da API (`app`) e do banco relacional (`db`), permitindo subir o ambiente completo com um único comando (`docker compose up --build`).

##### **RNF-13** - Documentação Interativa de API (OpenAPI / Swagger)
A API deve disponibilizar documentação interativa em conformidade com a especificação **OpenAPI 3.0 / Swagger UI** no endpoint `/docs`, detalhando schemas de entrada/saída, códigos de status HTTP e headers de autenticação Bearer JWT.
