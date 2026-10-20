# Guia de Desenvolvimento

Este guia explica **onde colocar cada parte do código e como implementá-la** respeitando a arquitetura do projeto. Ele serve tanto para os desenvolvedores do grupo quanto para assistentes de IA: quem for implementar qualquer coisa deve ler este documento antes de criar ou alterar arquivos.

---

## 1. Fontes da Verdade

Antes de implementar, consulte os documentos abaixo. Em caso de conflito entre o código e a documentação, **a documentação prevalece**; se a documentação estiver errada, corrija-a no mesmo PR.

| Documento | O que define |
| :--- | :--- |
| `docs/requisitos-funcionais.md` | O que o sistema deve fazer (RF-01 a RF-27). |
| `docs/requisitos-nao-funcionais.md` | Arquitetura, segurança, banco, Docker e testes (RNF-01 a RNF-16). |
| `docs/ddd/linguagem-ubiqua.md` | Nomes oficiais do domínio, máquina de estados da OS e o mapeamento entre conceitos e código. |
| `docs/estrutura-de-pastas.md` | Por que a estrutura de pastas é como é, incluindo a autenticação JWT. |
| `docs/guia-de-desenvolvimento.md` | Este guia: como implementar cada coisa. |

---

## 2. Arquitetura em Camadas

O sistema é um monólito em camadas (RNF-01) com o domínio isolado (RNF-02).

```text
src/
├── domain/           Regras de negócio puras (Python puro)
│   ├── entities/         Entidades e raízes de agregado
│   ├── value_objects/    Objetos de valor imutáveis
│   ├── events/           Eventos de domínio, um arquivo por evento
│   └── repositories/     Portas (interfaces ABC) de persistência
├── application/      Orquestração dos casos de uso
│   ├── use_cases/        Um arquivo por caso de uso
│   ├── ports/            Interfaces de serviços técnicos (token, hash de senha)
│   ├── events/           Event Dispatcher síncrono em memória
│   └── handlers/         Handlers que reagem aos eventos de domínio
├── infrastructure/   Detalhes técnicos (banco, bibliotecas externas)
│   ├── config.py         Leitura e validação das variáveis de ambiente
│   ├── database/         Engine, sessão, unidade de trabalho e modelos do SQLAlchemy
│   ├── repositories/     Implementações das portas de repositório (PostgreSQL)
│   └── security/         Implementações de JWT e hash de senha
└── presentation/     Entrada HTTP (rotas, DTOs, autenticação das rotas)
    ├── main.py           Criação do app FastAPI e registro dos routers
    ├── container.py      Montagem das dependências (único ponto que importa infrastructure)
    ├── routers/          Rotas FastAPI, um arquivo por recurso
    ├── schemas/          DTOs de entrada e saída, um arquivo por recurso
    └── middlewares/      Validação do token e rate limiting das rotas
migrations/           Migrations do Alembic (seção 8.1)
tests/
├── unit/             Testes sem banco e sem HTTP
└── integration/      Testes dos fluxos de ponta a ponta
```

### 2.1. Regra de Dependência

As dependências apontam sempre **para dentro**, em direção ao domínio. Esta é a regra mais importante do projeto.

| Camada | Pode importar de | **Nunca** importa de |
| :--- | :--- | :--- |
| `domain` | Apenas a biblioteca padrão do Python e o próprio `domain` | `application`, `infrastructure`, `presentation`, frameworks web, ORM, drivers de banco, bibliotecas de JWT |
| `application` | `domain` e `application` | `infrastructure`, `presentation` |
| `infrastructure` | `domain`, `application` e bibliotecas externas | `presentation` |
| `presentation` | `application`, `domain` (para tipos) e o framework web | `infrastructure`, exceto em `presentation/container.py`, o ponto de montagem das dependências |

Se um caso de uso precisa de algo técnico (banco, token, hash), ele depende de uma **interface** (porta) e recebe a implementação pelo construtor. Nunca instancia a implementação diretamente.

O `presentation/container.py` é o único arquivo que conhece as implementações. Na subida da aplicação, ele lê a configuração e cria os objetos únicos (engine, fábrica de sessões, serviços de token e de hash). Para cada caso de uso, ele oferece às rotas, por `Depends`, uma função `obter_<caso_de_uso>` que monta a sessão, os repositórios e o caso de uso da requisição. O `presentation/main.py` só cria o app, registra os routers e chama o container.

### 2.2. Porta e Adaptador

Toda dependência externa segue o mesmo padrão:

1. A **porta** (interface ABC) fica no domínio, se for persistência, ou em `application/ports/`, se for serviço técnico.
2. O **adaptador** (implementação concreta) fica em `infrastructure/`.
3. O caso de uso recebe a porta pelo construtor.

| Porta | Adaptador |
| :--- | :--- |
| `domain/repositories/ordem_servico_repository.py` | `infrastructure/repositories/postgres_ordem_servico_repository.py` |
| `domain/repositories/usuario_repository.py` | `infrastructure/repositories/postgres_usuario_repository.py` |
| `application/ports/token_service.py` | `infrastructure/security/jwt_token_service.py` |
| `application/ports/password_hasher.py` | `infrastructure/security/bcrypt_password_hasher.py` |

---

## 3. Onde Colocar Cada Coisa

| Estou criando... | Pasta | Nome do arquivo | Exemplo |
| :--- | :--- | :--- | :--- |
| Entidade ou raiz de agregado | `src/domain/entities/` | nome da entidade em snake_case | `veiculo.py` → `class Veiculo` |
| Objeto de valor | `src/domain/value_objects/` | nome do VO em snake_case | `placa.py` → `class Placa` |
| Enumeração do domínio | `src/domain/value_objects/` | nome do enum | `status_os.py` → `class StatusOS` |
| Exceção de regra de negócio | `src/domain/` | `exceptions.py` | `TransicaoDeStatusInvalida` |
| Interface de persistência | `src/domain/repositories/` | `<entidade>_repository.py` | `cliente_repository.py` → `class ClienteRepository(ABC)` |
| Implementação de persistência | `src/infrastructure/repositories/` | `postgres_<entidade>_repository.py` | `postgres_cliente_repository.py` |
| Caso de uso | `src/application/use_cases/` | verbo + objeto | `aprovar_orcamento.py` → `class AprovarOrcamento` |
| Interface de serviço técnico | `src/application/ports/` | nome do serviço | `token_service.py` → `class TokenService(ABC)` |
| Implementação de serviço técnico | `src/infrastructure/<assunto>/` | tecnologia + serviço | `jwt_token_service.py` |
| Rota HTTP | `src/presentation/routers/` | nome do recurso no plural | `ordens_servico.py` → `router = APIRouter()` |
| DTO de entrada ou saída da API | `src/presentation/schemas/` | nome do recurso no singular | `ordem_servico.py` → `CriarOSRequest`, `OSResponse` |
| Evento de domínio | `src/domain/events/` | nome do evento + `_event` | `orcamento_aprovado_event.py` → `class OrcamentoAprovadoEvent` |
| Event Dispatcher | `src/application/events/` | `event_dispatcher.py` | `class EventDispatcher` |
| Handler de evento | `src/application/handlers/` | ação + `_handler` | `baixa_estoque_handler.py` → `class BaixaEstoqueHandler` |
| Engine, sessão e unidade de trabalho do SQLAlchemy | `src/infrastructure/database/` | nome do assunto | `engine.py`, `unidade_de_trabalho.py` |
| Modelo do ORM (tabela) | `src/infrastructure/database/` | `<entidade>_model.py` | `cliente_model.py` → `class ClienteModel` |
| Configuração por variáveis de ambiente | `src/infrastructure/` | `config.py` | `class Configuracao(BaseSettings)` |
| Ponto de entrada da API | `src/presentation/` | `main.py` | `app = FastAPI(...)` |
| Montagem das dependências | `src/presentation/` | `container.py` | `obter_autenticar_usuario()` |
| Validação de token nas rotas | `src/presentation/middlewares/` | `dependencies.py` | — |
| Rate limiting das rotas públicas | `src/presentation/middlewares/` | `rate_limit.py` | `limiter = Limiter(...)` |
| Teste unitário | `tests/unit/` | `test_<arquivo testado>.py` | `test_placa.py` |
| Teste de integração | `tests/integration/` | `test_<fluxo>.py` | `test_fluxo_aprovacao_orcamento.py` |
| Migration do banco | `migrations/versions/` (raiz do projeto) | gerado pelo Alembic | `<revisão>_cria_tabela_cliente.py` |
| Relatório de segurança | `docs/security/` | — | relatório da análise de vulnerabilidades (RNF-07) |

Se algo não se encaixa em nenhuma linha desta tabela, **não crie uma pasta nova por conta própria**: discuta com o grupo e, se aprovado, atualize esta tabela e `docs/estrutura-de-pastas.md` no mesmo PR.

---

## 4. Convenções

### 4.1. Nomes

* Use os termos da **Linguagem Ubíqua** em português: `OrdemServico`, `Cliente`, `Veiculo`, `Servico`, `Peca`, `Orcamento`, `StatusOS`. Não traduza para o inglês e não invente sinônimos (ex.: não use `Pedido` no lugar de `OrdemServico`).
* Identificadores sem acentos nem cedilha: `Veiculo`, `Peca`, `Orcamento`.
* Arquivos e funções em `snake_case`; classes em `PascalCase`; constantes em `UPPER_SNAKE_CASE`.
* Os valores de `StatusOS` são exatamente os da seção 5 da Linguagem Ubíqua: `RECEBIDA`, `EM_DIAGNOSTICO`, `AGUARDANDO_APROVACAO`, `AGUARDANDO_PECA`, `AGUARDANDO_EXECUCAO`, `EM_EXECUCAO`, `FINALIZADA`, `ENTREGUE`, `CANCELADA`.

### 4.2. Imports

Imports absolutos a partir de `src/`, como na Linguagem Ubíqua:

```python
from domain.entities.ordem_servico import OrdemServico
from domain.value_objects.placa import Placa
```

### 4.3. Pacotes

Toda pasta dentro de `src/` deve ter um `__init__.py`. Ao criar uma pasta nova (depois de aprovada), crie também o `__init__.py`.

---

## 5. Receitas

### 5.1. Criar um Objeto de Valor

Objetos de valor são **imutáveis** e **se validam na criação**: um VO inválido nunca deve existir.

```python
# src/domain/value_objects/placa.py
import re
from dataclasses import dataclass

from domain.exceptions import PlacaInvalida

_PADRAO_ANTIGO = re.compile(r"^[A-Z]{3}[0-9]{4}$")
_PADRAO_MERCOSUL = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")


@dataclass(frozen=True)
class Placa:
    valor: str

    def __post_init__(self):
        if not (_PADRAO_ANTIGO.match(self.valor) or _PADRAO_MERCOSUL.match(self.valor)):
            raise PlacaInvalida(self.valor)
```

Checklist:
- [ ] `@dataclass(frozen=True)` (ou classe sem setters).
- [ ] Validação no `__post_init__`, lançando exceção de `domain/exceptions.py`.
- [ ] Teste unitário em `tests/unit/` cobrindo valores válidos e inválidos.

### 5.2. Criar uma Entidade

Entidades têm identidade e **protegem as próprias regras**. Quem altera o estado é um método da entidade, nunca uma atribuição feita de fora.

```python
# src/domain/entities/ordem_servico.py (trecho ilustrativo)
from domain.exceptions import TransicaoDeStatusInvalida
from domain.value_objects.status_os import StatusOS


class OrdemServico:
    def concluir_manutencao(self) -> None:
        if self.status != StatusOS.EM_EXECUCAO:
            raise TransicaoDeStatusInvalida(self.status, StatusOS.FINALIZADA)
        self._mudar_status(StatusOS.FINALIZADA)
```

Regras que **ficam obrigatoriamente no domínio**:
- Máquina de estados da OS e bloqueio de transições inválidas (Linguagem Ubíqua §5, RF-16 a RF-26).
- Timestamps de abertura, início da execução e finalização (RF-13, RF-20, RF-21) e registro de cada transição no histórico de status (RF-24).
- Cálculo do orçamento: subtotal de serviços + soma de `quantidade × preço_unitario` das peças, com valores congelados (RF-17, RNF-11).
- Reserva, pendência, prioridade pela OS mais antiga, baixa e estorno de peças, sem saldo negativo (RF-18 a RF-20).
- Cálculo da estimativa de entrega (RF-25).
- Validação de CPF, CNPJ e placa (RF-05, RF-08).

### 5.3. Criar uma Porta e um Adaptador de Repositório

1. Porta no domínio:

```python
# src/domain/repositories/cliente_repository.py
from abc import ABC, abstractmethod

from domain.entities.cliente import Cliente


class ClienteRepository(ABC):
    @abstractmethod
    async def salvar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    async def buscar_por_documento(self, documento: str) -> Cliente | None: ...
```

2. Adaptador na infraestrutura, herdando da porta:

```python
# src/infrastructure/repositories/postgres_cliente_repository.py
from domain.repositories.cliente_repository import ClienteRepository


class PostgresClienteRepository(ClienteRepository):
    ...
```

A porta recebe e devolve **entidades do domínio**, nunca modelos do ORM. A conversão entre entidade e tabela acontece dentro do adaptador.

Os métodos das portas de repositório são `async def`, porque o SQLAlchemy roda no modo assíncrono (seção 8.1). O adaptador carrega as coleções da entidade junto com a consulta (`selectinload`), pois o carregamento preguiçoso não funciona no modo assíncrono.

### 5.4. Criar um Caso de Uso

Um arquivo por caso de uso. O caso de uso recebe as portas pelo construtor e expõe um único método assíncrono `executar`.

```python
# src/application/use_cases/criar_os.py (trecho ilustrativo)
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class CriarOS:
    def __init__(self, clientes: ClienteRepository, ordens: OrdemServicoRepository):
        self._clientes = clientes
        self._ordens = ordens

    async def executar(self, documento_cliente: str, placa: str) -> OrdemServico:
        cliente = await self._clientes.buscar_por_documento(documento_cliente)
        ...
```

O caso de uso **orquestra** (busca, chama métodos das entidades, salva). Se aparecer um `if` de regra de negócio no caso de uso, ele provavelmente deveria estar na entidade.

Operações que precisam ser **atômicas** (RNF-08) rodam dentro de uma única transação de banco:

* criação da OS com seus itens;
* conclusão do orçamento com reserva das peças e registro das pendências (RF-17, RF-18);
* atualização de saldo com alocação às OS pendentes e liberação de OS em `AGUARDANDO_PECA` (RF-12, RF-19);
* início da execução com baixa das peças reservadas (RF-20);
* rejeição e cancelamento com estorno das reservas (RF-18, RF-23, RF-26);
* toda transição de status com o registro no histórico (RF-24).

Nenhuma dessas operações pode deixar o saldo disponível negativo (RF-12).

### 5.5. Criar uma Rota HTTP

1. Defina os DTOs de entrada e saída em `src/presentation/schemas/<recurso>.py` e a rota em `src/presentation/routers/<recurso>.py` (RNF-16).
2. A rota converte o DTO de entrada, chama o caso de uso e converte o resultado no DTO de saída.
3. A rota **não contém regra de negócio** e não acessa o repositório diretamente.
4. Use os códigos HTTP `200`, `201`, `400`, `401`, `403`, `404`, `422` e `500`. `401` indica token ausente ou inválido e `403` indica perfil sem permissão (RNF-03). Exceções do domínio são traduzidas para esses códigos na camada `presentation`.

### 5.6. Proteger uma Rota com JWT

* **Toda** rota administrativa e operacional exige token (RNF-03).
* As **únicas** rotas públicas são a consulta de status da OS (RF-25) e a aprovação ou rejeição do orçamento (RF-26). As duas exigem o número da OS junto com o CPF/CNPJ do titular e têm rate limiting com SlowAPI (RNF-05).
* A validação do token e a checagem do perfil (Atendente, Mecânico, Gerente) ficam em `src/presentation/middlewares/dependencies.py`, como dependências do FastAPI (`Depends`). Toda rota protegida declara a dependência, e uma rota sem ela fica pública.
* O login é o caso de uso `application/use_cases/autenticar_usuario.py`, que usa as portas `TokenService` e `PasswordHasher`.
* Senhas são guardadas apenas como hash; a chave de assinatura do JWT vem de variável de ambiente (RNF-06).

### 5.7. Escrever Testes

| Tipo | Pasta | O que testa | Usa banco? |
| :--- | :--- | :--- | :--- |
| Unitário | `tests/unit/` | Entidades, objetos de valor e casos de uso (RNF-12) | Não: use repositórios em memória que implementam a porta |
| Integração | `tests/integration/` | Fluxos completos pelas rotas HTTP, com adaptadores reais (RNF-13) | Sim |

Os testes de código assíncrono são funções `async def`; o pytest-asyncio está configurado com `asyncio_mode = "auto"` no `pyproject.toml`, então não é preciso marcar cada teste.

Exemplo de repositório em memória para testes unitários:

```python
class OrdemServicoRepositoryEmMemoria(OrdemServicoRepository):
    def __init__(self):
        self.dados = {}

    async def salvar(self, os):
        self.dados[os.id] = os

    async def buscar_por_id(self, id):
        return self.dados.get(id)
```

A cobertura deve ser de pelo menos **80%** nos domínios críticos (RNF-14). Todo código novo em `domain/` e `application/` deve vir acompanhado de testes.

---

## 6. Segurança

* Nunca commite senhas, chaves de JWT ou credenciais de banco (RNF-06). Use variáveis de ambiente; o `.env` é ignorado pelo Git e o `.env.example` lista as variáveis sem valores reais.
* Senhas de usuário são armazenadas somente como hash.
* O relatório da análise de vulnerabilidades vai em `docs/security/` (RNF-07).

---

## 7. Fluxo de Git

* Não faça commit direto na `main`. Crie uma branch e abra um PR. A `main` é protegida no GitHub: o merge exige PR com 1 aprovação de outro integrante e push forçado é bloqueado (exigência do enunciado).
* Nomes de branch: `<tipo>/<descricao-curta>`, por exemplo `feat/crud-clientes`, `fix/validacao-cnpj`, `chore/estrutura-conforme-docs`.
* Mensagens de commit em português, no formato `<tipo>: <descrição>`, com os tipos `feat`, `fix`, `chore`, `docs`, `test`, `refactor`.
* Sempre que possível, cite o requisito no corpo do commit ou no PR (ex.: "Implementa RF-04").

---

## 8. Decisões Técnicas

### 8.1. Decididas

| Decisão | Definição |
| :--- | :--- |
| Linguagem | Python 3.12 (RNF-02) |
| Framework web | FastAPI + Uvicorn, com Swagger em `/docs` (RNF-16) |
| Banco de dados | PostgreSQL 16 (RNF-09) |
| ORM | SQLAlchemy 2.0 (RNF-04) |
| Modo do SQLAlchemy | Assíncrono, com o driver asyncpg (issue #3). São `async def` as portas de repositório, as portas de serviço que bloqueiam (como `PasswordHasher`, que executa o bcrypt com `asyncio.to_thread`), os casos de uso e as rotas. `TokenService` é síncrono, pois não faz I/O. Carregamento preguiçoso proibido: as coleções são carregadas com `selectinload`. Testes com pytest-asyncio (`asyncio_mode = "auto"`) |
| JWT e hash de senha | PyJWT e bcrypt (RF-01, RF-03) |
| Gerenciamento de dependências | `uv` com `pyproject.toml` e lockfile `uv.lock`. Comandos: `uv sync` (instala o ambiente), `uv add <pacote>` (adiciona dependência), `uv run pytest` (executa sem ativar o venv) |
| Imports a partir de `src/` | `PYTHONPATH=src`: `pythonpath = ["src"]` no pytest (`pyproject.toml`), `ENV PYTHONPATH=/app/src` no Dockerfile e `PYTHONPATH=src` no `.env` para a IDE |
| Lint e formatação | Ruff (`ruff check` e `ruff format`), configurado no `pyproject.toml` |
| Testes e cobertura | pytest + pytest-cov (RNF-12 a RNF-14) |
| Migrations | Alembic com o template `async` (issue #4). A pasta `migrations/` e o `alembic.ini` ficam na raiz do projeto; cada mudança de schema é gerada com `uv run alembic revision --autogenerate -m "<descrição>"`, revisada antes do commit e aplicada com `alembic upgrade head` na subida do container. O Dockerfile precisa copiar `migrations/` e `alembic.ini` |
| Rate limiting | SlowAPI com contador em memória (RNF-05) |
| Rotas e DTOs | `presentation/routers/` e `presentation/schemas/`, um arquivo por recurso |
| Estrutura de pastas | Alinhada à seção 6 do modelo C4 (issue #9): `domain/events/`, `application/events/`, `application/handlers/`, `infrastructure/database/` e `presentation/middlewares/` (seções 2 e 3) |
| Configuração | `infrastructure/config.py` com pydantic-settings (issue #9). A configuração é lida e validada na subida da aplicação, nunca no import do módulo. Só o `presentation/container.py` importa o módulo, e os demais objetos recebem os valores pelo construtor |
| Ponto de entrada e montagem | `presentation/main.py` cria o app e registra os routers; `presentation/container.py` monta as dependências (issue #9) |
| CI (GitHub Actions) | Opcional; implementar somente se houver tempo ao final |

### 8.2. Em Aberto

Os itens abaixo **ainda não foram decididos** pelo grupo. Não assuma uma escolha sem combinar antes; quando a decisão for tomada, mova o item para 8.1.

| Decisão | Opções levantadas e custos |
| :--- | :--- |
| Ferramentas de vulnerabilidade (RNF-07) | Proposta inicial: pip-audit (dependências), Bandit (código), Trivy (imagem Docker) e Dependabot (alertas no GitHub). Falta confirmação do grupo. |
| Teste de desempenho (RNF-10) | Opções: Locust (cenários em Python, relatório HTML com p95), k6 (limite de p95 declarado no script, em JavaScript) ou script próprio com httpx. |

## 9. Instruções para Assistentes de IA

Se você é um assistente de IA trabalhando neste repositório, siga estas regras:

1. **Leia antes de escrever.** Consulte este guia, a Linguagem Ubíqua e o requisito (RF/RNF) relacionado à tarefa antes de criar ou alterar arquivos.
2. **Use a tabela da seção 3** para decidir onde cada arquivo fica. Não crie pastas fora dela sem que o usuário peça explicitamente; se criar, atualize a seção 3 e `docs/estrutura-de-pastas.md`.
3. **Respeite a regra de dependência da seção 2.1.** Antes de terminar, confira os imports de cada arquivo alterado: nada em `domain/` pode importar framework, ORM, banco ou biblioteca de JWT.
4. **Regras de negócio ficam no domínio** (seção 5.2), não em casos de uso nem em rotas.
5. **Use os nomes da Linguagem Ubíqua.** Não invente termos nem traduza para o inglês.
6. **Não invente requisitos.** Se a documentação não define algo (seção 8), pergunte ao usuário em vez de escolher sozinho.
7. **Escreva testes** junto com o código, conforme a seção 5.7.
8. **Nunca coloque segredos no código** (seção 6).
9. **Ao terminar**, informe quais requisitos (RF/RNF) a mudança atende e se alguma decisão nova foi tomada.
