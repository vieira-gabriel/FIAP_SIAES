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
| `docs/CHANGELOG.md` | Motivo de cada alteração estrutural ou arquitetural da documentação. |

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
    └── middlewares/      Validação do token, rate limiting e tratamento de erros das rotas
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
| `domain/repositories/cliente_repository.py` | `infrastructure/repositories/postgres_cliente_repository.py` |
| `domain/repositories/veiculo_repository.py` | `infrastructure/repositories/postgres_veiculo_repository.py` |
| `domain/repositories/servico_repository.py` | `infrastructure/repositories/postgres_servico_repository.py` |
| `domain/repositories/peca_repository.py` | `infrastructure/repositories/postgres_peca_repository.py` |
| `domain/repositories/estoque_repository.py` | `infrastructure/repositories/postgres_estoque_repository.py` |
| `application/ports/token_service.py` | `infrastructure/security/jwt_token_service.py` |
| `application/ports/password_hasher.py` | `infrastructure/security/bcrypt_password_hasher.py` |
| `application/ports/unidade_de_trabalho.py` | `infrastructure/database/unidade_de_trabalho.py` |
| `application/ports/verificador_do_banco.py` | `infrastructure/database/verificador_do_banco.py` |

---

## 3. Onde Colocar Cada Coisa

| Estou criando... | Pasta | Nome do arquivo | Exemplo |
| :--- | :--- | :--- | :--- |
| Entidade ou raiz de agregado | `src/domain/entities/` | nome da entidade em snake_case | `veiculo.py` → `class Veiculo` |
| Objeto de valor | `src/domain/value_objects/` | nome do VO em snake_case | `placa.py` → `class Placa` |
| Base comum de objetos de valor | `src/domain/value_objects/` | nome da base em snake_case | `documento.py` → `class Documento` |
| Enumeração do domínio | `src/domain/value_objects/` | nome do enum | `status_os.py` → `class StatusOS` |
| Exceção de regra de negócio | `src/domain/` | `exceptions.py` | `TransicaoDeStatusInvalida` |
| Interface de persistência | `src/domain/repositories/` | `<entidade>_repository.py` | `cliente_repository.py` → `class ClienteRepository(ABC)` |
| Implementação de persistência | `src/infrastructure/repositories/` | `postgres_<entidade>_repository.py` | `postgres_cliente_repository.py` |
| Caso de uso | `src/application/use_cases/` | verbo + objeto | `aprovar_orcamento.py` → `class AprovarOrcamento` |
| Interface de serviço técnico | `src/application/ports/` | nome do serviço | `token_service.py` → `class TokenService(ABC)` |
| Implementação de serviço técnico | `src/infrastructure/<assunto>/` | tecnologia + serviço | `jwt_token_service.py` |
| Rota HTTP | `src/presentation/routers/` | nome do recurso no plural | `ordens_servico.py` → `router = APIRouter()` |
| DTO de entrada ou saída da API | `src/presentation/schemas/` | nome do recurso no singular | `ordem_servico.py` → `CriarOSRequest`, `OSResponse` |
| Evento de domínio | `src/domain/events/` | nome do evento + `_event` | `orcamento_finalizado_event.py` → `class OrcamentoFinalizadoEvent` |
| Event Dispatcher | `src/application/events/` | `event_dispatcher.py` | `class EventDispatcher` |
| Handler de evento | `src/application/handlers/` | ação + `_handler` | `baixa_estoque_handler.py` → `class BaixaEstoqueHandler` |
| Engine, sessão, unidade de trabalho e `Base` do ORM do SQLAlchemy | `src/infrastructure/database/` | nome do assunto | `engine.py`, `unidade_de_trabalho.py`, `base.py` |
| Modelo do ORM (tabela) | `src/infrastructure/database/` | `<entidade>_model.py` | `cliente_model.py` → `class ClienteModel` |
| Configuração por variáveis de ambiente | `src/infrastructure/` | `config.py` | `class Configuracao(BaseSettings)` |
| Ponto de entrada da API | `src/presentation/` | `main.py` | `app = FastAPI(...)` |
| Montagem das dependências | `src/presentation/` | `container.py` | `obter_token_service()` |
| Validação de token nas rotas | `src/presentation/middlewares/` | `dependencies.py` | — |
| Rate limiting das rotas públicas | `src/presentation/middlewares/` | `rate_limit.py` | `limiter = Limiter(...)` |
| Tradução das exceções em respostas HTTP | `src/presentation/middlewares/` | `tratamento_de_erros.py` | `registrar_tratamento_de_erros(app)` |
| Teste unitário | `tests/unit/` | `test_<arquivo testado>.py` | `test_placa.py` |
| Teste de integração | `tests/integration/` | `test_<fluxo>.py` | `test_fluxo_aprovacao_orcamento.py` |
| Migration do banco | `migrations/versions/` (raiz do projeto) | gerado pelo Alembic | `<revisão>_cria_tabela_cliente.py` |
| Relatório de segurança | `docs/security/` | — | relatório da análise de vulnerabilidades (RNF-07) |
| Workflow de CI | `.github/workflows/` (raiz do projeto) | nome do pipeline | `ci.yml` |

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

### 4.4. Construção de Entidades

* Construa as entidades com **argumentos nomeados**. A ordem dos campos da `dataclass` não faz parte do contrato (em `OrdemServico`, `mecanico_id` vem antes de `id`), e o adaptador de persistência não deve depender dela.
* O construtor só **reconstitui** uma entidade já existente e nunca cria registros novos. O que é criação com efeito colateral vem de uma fábrica, como `OrdemServico.abrir`, que grava o registro de abertura no histórico. Um adaptador que reconstitui uma OS do banco usa o construtor, com o histórico completo e em ordem.

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
from collections.abc import Collection
from datetime import UTC, datetime
from uuid import UUID

from domain.entities.historico_status_os import HistoricoStatusOS
from domain.exceptions import TransicaoDeStatusInvalida
from domain.value_objects.origem_transicao import OrigemTransicao
from domain.value_objects.status_os import StatusOS


class OrdemServico:
    def concluir_manutencao(self, usuario_id: UUID) -> None:
        self.data_finalizacao = self._mudar_status(
            StatusOS.FINALIZADA,
            de={StatusOS.EM_EXECUCAO},
            origem=OrigemTransicao.USUARIO,
            usuario_id=usuario_id,
        )

    def _mudar_status(
        self,
        destino: StatusOS,
        *,
        de: Collection[StatusOS],
        origem: OrigemTransicao,
        usuario_id: UUID | None = None,
        motivo: str | None = None,
    ) -> datetime:
        if self.status not in de:
            raise TransicaoDeStatusInvalida(self.status, destino)
        momento = datetime.now(UTC)
        self._acrescentar_ao_historico(
            HistoricoStatusOS(self.status, destino, momento, origem, usuario_id, motivo)
        )
        self.status = destino
        return momento
```

Cada transição declara de quais status parte, e só `_mudar_status` altera o `status` e grava o registro no histórico (RF-24); os eventos de domínio se encaixam nesse mesmo ponto. A origem do registro (`USUARIO`, `CLIENTE` ou `SISTEMA`) vem de quem executa a transição, conforme a Linguagem Ubíqua §5. O `historico` da OS é uma tupla somente leitura (RF-24: os registros não podem ser alterados nem removidos), e o registro de abertura nasce em `OrdemServico.abrir`: o construtor só reconstitui uma OS, então o adaptador de persistência precisa carregar o histórico completo e em ordem.

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
from domain.value_objects.documento import Documento


class ClienteRepository(ABC):
    @abstractmethod
    async def salvar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    async def buscar_por_documento(self, documento: Documento) -> Cliente | None: ...
```

2. Adaptador na infraestrutura, herdando da porta:

```python
# src/infrastructure/repositories/postgres_cliente_repository.py
from domain.repositories.cliente_repository import ClienteRepository


class PostgresClienteRepository(ClienteRepository):
    ...
```

A porta recebe e devolve **entidades do domínio**, nunca modelos do ORM. Os critérios de busca também são objetos de valor (`Documento`, `Placa`), e não `str`: assim o valor chega à porta já validado e normalizado. A conversão entre entidade e tabela acontece dentro do adaptador.

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

    async def executar(self, documento_cliente: Documento, placa: Placa) -> OrdemServico:
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
* exclusão lógica do cliente com a exclusão lógica dos veículos dele (RF-06, RF-09);
* toda transição de status com o registro no histórico (RF-24).

Nenhuma dessas operações pode deixar o saldo disponível negativo (RF-12).

### 5.5. Criar uma Rota HTTP

1. Defina os DTOs de entrada e saída em `src/presentation/schemas/<recurso>.py` e a rota em `src/presentation/routers/<recurso>.py` (RNF-16).
2. A rota converte o DTO de entrada, chama o caso de uso e converte o resultado no DTO de saída.
3. A rota **não contém regra de negócio** e não acessa o repositório diretamente.
4. Use os códigos HTTP `200`, `201`, `400`, `401`, `403`, `404`, `422` e `500`. `401` indica token ausente ou inválido e `403` indica perfil sem permissão (RNF-03). Exceções do domínio são traduzidas para esses códigos na camada `presentation`.
5. Basta a rota deixar a exceção do domínio subir: os tratadores de `presentation/middlewares/tratamento_de_erros.py` fazem a tradução, sempre com o corpo `ErroResponse` (`presentation/schemas/erro.py`):

   | Exceção | Código HTTP | `codigo` no corpo |
   | :--- | :--- | :--- |
   | `ValorInvalido` (CPF, placa, número da OS...) | `400` | `VALOR_INVALIDO` |
   | `CredenciaisInvalidas` e token ausente ou inválido | `401` | `NAO_AUTENTICADO` |
   | `AcessoNegado` (operação que o usuário não pode fazer, como iniciar a execução de uma OS alheia) e perfil sem permissão | `403` | `SEM_PERMISSAO` |
   | `EntidadeNaoEncontrada` | `404` | `ENTIDADE_NAO_ENCONTRADA` |
   | `RegraDeNegocioViolada` (transição inválida, saldo insuficiente...) | `422` | `REGRA_DE_NEGOCIO_VIOLADA` |
   | Corpo da requisição fora do DTO (campo ausente, tipo errado) | `422` | `ENTRADA_INVALIDA`, com os campos em `detalhes` |
   | Qualquer outra exceção | `500` | `ERRO_INTERNO`, sem mensagem interna nem stack trace; a causa vai para o log |

   ```json
   {"codigo": "VALOR_INVALIDO", "mensagem": "CPF inválido.", "detalhes": []}
   ```
6. Nas rotas que gravam, declare a dependência do caso de uso com `Depends(obter_<caso_de_uso>, scope="function")`. A unidade de trabalho confirma a transação ao sair da dependência, e o FastAPI, sem esse `scope`, só sai dela depois de enviar a resposta: uma falha no commit chegaria ao cliente como sucesso. Exemplo em `presentation/routers/clientes.py`.

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

Como executar:

```bash
# Só os testes unitários, sem banco
uv run pytest tests/unit

# Testes de integração: com o .env preenchido, suba o PostgreSQL publicado em 127.0.0.1
docker compose -f docker-compose.yml -f docker-compose.testes.yml up -d db
uv run pytest tests/integration
```

Fora do CI, sem o `.env` preenchido ou sem o banco no ar, os testes de integração são pulados, e `uv run pytest` roda só os unitários. No CI (`CI=true`), eles falham em vez de serem pulados.

As fixtures de `tests/integration/conftest.py` servem de base para todo teste de integração:

| Fixture | O que oferece |
| :--- | :--- |
| `banco_de_teste` | Banco `<POSTGRES_DB>_test`, recriado no início da sessão de testes, com as migrations aplicadas, e apagado no final. O banco de desenvolvimento não é tocado |
| `engine` | Engine conectada ao banco de teste |
| `conexao` | Conexão com uma transação desfeita ao final do teste, para um teste não enxergar o que outro gravou |
| `fabrica_de_sessoes` | Sessões presas à transação do teste; o `commit` da unidade de trabalho só fecha um savepoint |
| `cliente_http` | Cliente `httpx` da aplicação real, com o ciclo de vida executado e as sessões presas à transação do teste |
| `banco_temporario` | Banco vazio e só do teste, para quem precisa de um banco próprio (migrations, login pela aplicação inteira); aponta `POSTGRES_DB` para ele |
| `banco_migrado` | O `banco_temporario` com as migrations aplicadas |

Exemplos de uso em `tests/integration/test_estrutura_de_integracao.py`.

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

Os repositórios em memória de todas as portas de repositório já existem em `tests/unit/conftest.py`, cada um com a sua fixture (`clientes`, `veiculos`, `usuarios`, `servicos`, `pecas`, `estoques` e `ordens`), junto com o `password_hasher` falso. Use-os nos testes de casos de uso em vez de criar uma cópia no arquivo do teste.

A cobertura deve ser de pelo menos **80%** nos domínios críticos (RNF-14). Todo código novo em `domain/` e `application/` deve vir acompanhado de testes.

---

## 6. Segurança

* Nunca commite senhas, chaves de JWT ou credenciais de banco (RNF-06). Use variáveis de ambiente; o `.env` é ignorado pelo Git e o `.env.example` lista as variáveis sem valores reais.
* Senhas de usuário são armazenadas somente como hash.
* O relatório da análise de vulnerabilidades vai em `docs/security/` (RNF-07).

---

## 7. Fluxo de Git

* Não faça commit direto na `main`. Crie uma branch e abra um PR. A `main` deve ser protegida no GitHub (exigência do enunciado): o merge exige PR com 1 aprovação de outro integrante, e o push forçado é bloqueado. O check "Lint, testes e segurança" do CI (seção 8.1) também precisa passar: ele deve estar marcado como obrigatório (*required status check*) na proteção da `main`. A configuração é feita pelo dono do repositório em Settings → Branches e está pendente (roadmap, Fase 0); até lá, a regra vale por combinação do grupo.
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
| Catálogo de serviços (RF-10, RF-11) | Rotas `/servicos` (issue #84): todos os perfis listam e consultam, só o Gerente cadastra, edita e exclui. O código do serviço é único, inclusive para serviços excluídos (`CodigoDeServicoJaCadastrado`, `422`), e a edição altera todos os dados. O `valor_base` é gravado como `NUMERIC(12, 2)` e trafega como texto no JSON (`"120.50"`), sem erro de ponto flutuante (RNF-11) |
| Gestão de peças (RF-12) | Rotas `/pecas` (issue #85): todos os perfis listam e consultam; Mecânico e Gerente repõem (`POST /pecas/{id}/reposicao`, soma à quantidade física) e ajustam (`PUT /pecas/{id}/quantidade-fisica`, nova quantidade absoluta); só o Gerente cadastra, edita e exclui. O cadastro cria a peça e o `EstoquePeca` na mesma transação, com quantidade física inicial opcional. As respostas trazem as quantidades física e reservada e o saldo disponível. O código de referência é gravado em maiúsculas e é único, inclusive para peças excluídas (`CodigoDePecaJaCadastrado`, `422`), e o preço trafega como texto no JSON. A peça excluída responde `404` em todas as rotas, e a exclusão é recusada com OS pendente (`PecaComPendencia`, `422`). O ajuste abaixo da quantidade reservada responde `422` (`QuantidadeFisicaAbaixoDaReservada`). Cada valor informado acima dos limites de `INTEGER` e `NUMERIC(12, 2)` é recusado no DTO com `422`; a soma da quantidade física com a reposição não é verificada e, se passar do limite do `INTEGER`, a gravação falha com `500` |
| Despacho dos eventos na transação (RNF-08) | Cada requisição monta o `EventDispatcher` com os handlers presos à sessão da unidade de trabalho (issue #89). Os handlers entram em `app.state.fabricas_de_handlers`, uma lista de pares `(tipo_do_evento, fabrica)`, em que a fabrica recebe a sessão e devolve o handler. O caso de uso despacha `collect_domain_events()` antes da confirmação; a falha de um handler desfaz a operação inteira. A lista já traz o `ReservaPecasHandler` (issue #93) e o `AlocacaoPecasPendentesHandler` (issue #94), registrados em `_fabricas_de_handlers`, no `container.py`; os demais handlers da Fase 5 entram nela |
| Abertura da OS (RF-13) | `POST /ordens-servico`, para Atendente e Gerente (issue #90). O corpo traz o documento e a placa, e opcionalmente os dados de `cliente` e de `veiculo`: sem eles, um cliente ou veículo que não existe responde `404`. A placa de um veículo de outro cliente responde `422` (`OSDeOutroCliente`). O número sai de `NumeroOS.gerar`; se já existir, é refeito com outro UUID, até 5 tentativas. Cliente, veículo e OS são gravados na mesma unidade de trabalho, e uma falha desfaz os três (RNF-08). O atendente é o usuário do token |
| Detalhamento da OS (RF-15) | `GET /ordens-servico/{id}`, para Atendente, Mecânico e Gerente (issue #108). Devolve a OS com cliente (`id` e `nome`), veículo (`id`, `placa`, `marca` e `modelo`), atendente e mecânico (só os ids), itens de serviço e de peça com os valores congelados e as quantidades reservada e pendente, orçamento (nulo enquanto não calculado), as datas, a estimativa de entrega e o histórico de status. Cliente e veículo excluídos continuam aparecendo, porque a OS guarda o histórico deles (RF-06, RF-09). A estimativa é calculada na consulta, com o momento atual (RF-25), e a OS inexistente responde `404`. Os valores monetários trafegam como texto no JSON |
| Consulta pública da OS (RF-25) | `POST /acompanhamento`, sem JWT (issue #96). O corpo traz o `numero` da OS e o `documento` do titular, que não vão na URL para não ficarem nos logs de acesso. O caso de uso `ConsultarOSPublica` busca a OS pelo número e compara o documento com o do cliente da OS, mesmo excluído. Número inexistente, número malformado, documento malformado e documento de outro titular respondem o mesmo `404` (`ENTIDADE_NAO_ENCONTRADA`), com a mesma mensagem; por isso o documento é validado dentro do caso de uso, e não no DTO, que responderia `400`. O número é aceito em minúsculas e com espaços, e o documento com ou sem pontuação. A resposta traz só o número, o status, o nome dos serviços, as peças pendentes (nome e quantidade), o valor total (nulo antes da conclusão do orçamento) e a estimativa de entrega do momento da consulta; não traz dados do cliente, placa, preços unitários nem histórico. O rate limiting de 10 requisições por minuto por IP (RNF-05) é da issue #97: até ela entrar, a rota não tem limite |
| Listagem de OS (RF-14) | `GET /ordens-servico`, para Atendente, Mecânico e Gerente (issue #107). Os filtros são opcionais e combináveis: `documento`, `placa`, `status`, `mecanico_id`, `abertura_de` e `abertura_ate`. A resposta traz, de cada OS, o número, o status, o nome do cliente, a placa, o nome do mecânico, a data de abertura e o total do orçamento (nulo enquanto não calculado), da abertura mais recente para a mais antiga; não há paginação. Documento ou placa sem cadastro devolvem a lista vazia com `200`. A placa vale para todos os veículos que a tiveram, inclusive os excluídos (`VeiculoRepository.listar_por_placa`), porque as OS deles continuam no histórico (RF-09); o documento vale para o cliente mesmo excluído. O período exige data e hora com fuso horário e início não posterior ao fim, senão responde `400`. A consulta não bloqueia as linhas |
| Atribuição do mecânico (RF-16) | `POST /ordens-servico/{id}/mecanico`, para Mecânico e Gerente (issue #91). O corpo é opcional: o Mecânico omite o `mecanico_id`, porque atribui a OS a si mesmo, e o Gerente informa o mecânico (sem o campo, `400`). A OS passa de `RECEBIDA` para `EM_DIAGNOSTICO`; fora de `RECEBIDA` responde `422`. O Mecânico não atribui a OS a outro (`AcessoNegado`, `403`), o indicado precisa ser um usuário com perfil Mecânico e ativo (`MecanicoIndisponivel`, `422`) e o usuário ou a OS inexistentes respondem `404`. O histórico grava o responsável pela atribuição (o Gerente, quando ele atribui), e não o mecânico indicado (RF-24). `OrdemServico.atribuir_mecanico` recebe o mecânico e o responsável como `Usuario` |
| Itens e conclusão do orçamento (RF-17) | Rotas de `/ordens-servico/{id}` para Mecânico e Gerente (issue #92): `POST /servicos` (corpo `servico_id`) e `POST /pecas` (corpo `peca_id` e `quantidade`) incluem o item e respondem `201` com a OS (status, itens e orçamento, nulo até a conclusão); `DELETE /servicos/{servico_id}` e `DELETE /pecas/{peca_id}` tiram o item e respondem `204`; `POST /orcamento` conclui o orçamento e responde `200`. Só serviço e peça ativos entram, uma vez cada, e só em `EM_DIAGNOSTICO`: o item excluído, o repetido e a OS fora do diagnóstico respondem `422`, e o catálogo ou a OS inexistentes respondem `404`. Quantidade que não seja inteiro positivo responde `400` (`0` e negativos) ou `422` (tipo errado ou acima do `INTEGER`). A conclusão congela os valores vigentes no momento dela, e reajustes posteriores do catálogo não mudam o orçamento (RNF-11). O `FinalizarOrcamento` salva a OS e despacha o `OrcamentoFinalizadoEvent` na mesma unidade de trabalho, então a falha de um handler desfaz a conclusão (RNF-08); a reserva das peças que reage ao evento é do `ReservaPecasHandler` (issue #93). Qualquer Mecânico ou Gerente altera os itens de qualquer OS em diagnóstico, não só o mecânico atribuído |
| Reserva das peças na conclusão do orçamento (RF-18) | O `ReservaPecasHandler`, em `application/handlers/` (issue #93), trata o `OrcamentoFinalizadoEvent` na transação da conclusão. Para cada peça da OS ainda pendente, em ordem de id (a mesma do `FinalizarOrcamento`, que já bloqueou os estoques), ele lê o estoque com bloqueio, junta as OS que já esperam a peça (`listar_pendentes_da_peca`, sem bloqueio) e a OS nova, aloca o saldo pela OS mais antiga com `EstoquePeca.alocar_pendencias` e aplica cada alocação com `OrdemServico.alocar_peca`: reserva o menor valor entre o pedido e o saldo e deixa a diferença pendente. No empate de data de abertura, a OS que já esperava vem antes da nova. Uma OS mais antiga que recebe saldo é relida com `buscar_por_id`, que a bloqueia depois do estoque, e é liberada de `AGUARDANDO_PECA` se ficar sem pendência; essa releitura pode entrar em impasse com o cancelamento (decisão "Repetição da transação em impasse"), o que só ocorre quando há saldo e pendência da mesma peça ao mesmo tempo. O handler é idempotente: a peça já reservada não é reservada de novo. A peça sem linha de estoque fica toda pendente. A repartição do saldo é o `alocar_saldo` do `AlocacaoPecasPendentesHandler`, o mesmo da reposição, e o `ReservaPecasHandler` só passa a OS nova a ele |
| Alocação das peças repostas (RF-19) | O `AlocacaoPecasPendentesHandler`, em `application/handlers/` (issue #94), trata o `SaldoPecaAtualizadoEvent` na transação da operação que aumentou o saldo: a reposição (`POST /pecas/{id}/reposicao`) e o ajuste da quantidade física para cima (`PUT /pecas/{id}/quantidade-fisica`); o estorno do cancelamento (issue #95) gera o mesmo evento. Com o estoque da peça já bloqueado pela operação, ele relê o estoque, aloca o saldo **atual** (e não o do evento, que pode estar antigo) às OS que têm a peça pendente, da mais antiga para a mais nova (`listar_pendentes_da_peca` e `EstoquePeca.alocar_pendencias`), e aplica cada alocação com `OrdemServico.alocar_peca`, relendo a OS com `buscar_por_id`, que a bloqueia. A OS em `AGUARDANDO_APROVACAO` recebe a reserva sem mudar o status, e a OS em `AGUARDANDO_PECA` que fica sem pendência passa a `AGUARDANDO_EXECUCAO` com origem `SISTEMA` e sem usuário no histórico. A falha de qualquer handler desfaz a operação inteira, inclusive a reposição (RNF-08). A releitura da OS depois do estoque pode cruzar com o cancelamento; a decisão "Repetição da transação em impasse" trata esse caso |
| Gestão de usuários (RF-03) | Rotas `/usuarios`, só para o Gerente (issue #81). A senha tem no mínimo 8 caracteres e no máximo 72 bytes, o limite do bcrypt, e muda só pela rota `PUT /usuarios/{id}/senha`. O Gerente não desativa o próprio acesso nem muda o próprio perfil (`AlteracaoDoProprioAcesso`, `422`), para a oficina não ficar sem Gerente. A listagem e o detalhamento mostram também os usuários desativados, para que possam ser reativados |
| Cancelamento pelo Gerente (RF-23, RF-18) | `POST /ordens-servico/{id}/cancelamento`, só para o Gerente (issue #95), com o corpo `{"motivo": "..."}`. O caso de uso `CancelarOS` bloqueia a OS com `buscar_por_id`, chama `OrdemServico.cancelar` (de `RECEBIDA` a `EM_EXECUCAO`; as pendências são descartadas) e despacha o `OSCanceladaEvent` na mesma transação. O `EstornoReservasHandler` bloqueia o estoque de cada peça em ordem de id e devolve a reserva com `EstoquePeca.estornar`; o `SaldoPecaAtualizadoEvent` do estorno vai para a alocação às OS que esperam a peça (RF-19), na mesma transação. A OS cancelada em `EM_EXECUCAO` não devolve nada, porque a baixa já ocorreu. O motivo em branco responde `422` (`MotivoObrigatorio`), e a OS fora de `RECEBIDA` a `EM_EXECUCAO`, como `FINALIZADA`, `ENTREGUE` e `CANCELADA`, também (`TransicaoDeStatusInvalida`). A rejeição do orçamento pelo cliente (issue #102) reutiliza o mesmo handler. A resposta é a OS com o novo status |
| Higienização do motivo contra XSS (RNF-04) | O motivo que contém o caractere `<` é recusado com `400` (`MotivoInvalido`, `VALOR_INVALIDO`), em `OrdemServico.cancelar`: o banco guarda o texto original e nenhum texto escapado. Acentos e os demais símbolos (`&`, `>`, aspas) são aceitos. A alternativa, escapar o HTML na entrada, grava o texto alterado no histórico (RF-24) e foi descartada pelo grupo na issue #95. A saída da API é JSON, que o cliente da API deve exibir como texto |
| Repetição da transação em impasse (RF-19, RF-23) | A alocação da reposição bloqueia o estoque e depois relê cada OS pendente com `buscar_por_id`, e o cancelamento bloqueia a OS e depois o estoque. Quando as duas se cruzam, o PostgreSQL aborta uma das transações (`deadlock detected`, SQLSTATE `40P01`). O grupo escolheu a opção (C) da antiga decisão em aberto: manter a ordem dos bloqueios e repetir a transação. `com_repeticao_em_impasse`, em `infrastructure/database/repeticao_em_impasse.py`, embrulha o caso de uso na montagem do container; ao receber um erro do banco com esse SQLSTATE, desfaz a transação da sessão e executa o caso de uso de novo, até 3 tentativas, e a terceira falha sobe como `500`. Qualquer outro erro sobe sem repetição. Recebem a repetição os casos de uso que podem ser a vítima do impasse: `CancelarOS`, `FinalizarOrcamento`, `ReporPeca` e `AjustarQuantidadeFisicaDaPeca`. Eles releem tudo do banco a cada tentativa e não gravam fora da transação, então repetir é seguro. O impasse continua possível, mas a requisição deixa de falhar por causa dele |
| Persistência da OS (RF-13, RF-19, RF-24) | Tabelas `ordens_servico`, `itens_servico`, `itens_peca` e `historico_status_os` (issue #88), com os quatro modelos em `infrastructure/database/ordem_servico_model.py`, porque os itens e o histórico só são gravados junto com a raiz do agregado. O número da OS é único, e a colisão de duas aberturas simultâneas vira `NumeroOSJaCadastrado` (`422`). Há chaves estrangeiras para cliente, veículo, usuários, serviços e peças (RNF-09). O orçamento é gravado como os dois subtotais, nulos quando não foi calculado. `itens_peca` repete as regras de quantidade de `ItemPeca` em CHECKs, e triggers recusam UPDATE, DELETE e TRUNCATE em `historico_status_os`: o adaptador só insere os registros novos (RF-24). Os itens voltam em ordem de nome, e o histórico em ordem de data e hora, com desempate pelo encadeamento dos status quando dois registros têm o mesmo instante. `buscar_por_id` e `buscar_por_numero` bloqueiam a OS lida (`SELECT ... FOR UPDATE`) até o fim da transação, então duas operações na mesma OS esperam uma pela outra, e as leituras de consulta também esperam uma escrita em andamento. A ordem dos bloqueios é OS e depois estoque: `FinalizarOrcamento` bloqueia a OS e então o estoque de cada peça, em ordem de id, antes de ler o catálogo, e o cancelamento e a rejeição com estorno (issues #95 e #102) seguem a mesma ordem. `listar_pendentes_da_peca` não bloqueia as OS, porque os casos de uso que a chamam já bloquearam o estoque da peça antes (`ExcluirPeca` e a alocação da reposição, issue #94); bloquear as OS depois do estoque inverteria a ordem e causaria impasse. Quem for alterar uma OS da lista, como a alocação da #94, a relê com `buscar_por_id`, que a bloqueia; essa releitura bloqueia a OS depois do estoque e pode entrar em impasse com o cancelamento; a decisão "Repetição da transação em impasse" trata esse caso |
| Item excluído do catálogo antes do congelamento (RF-11, RF-12, RF-17) | `congelar_valores`, e por ele `finalizar_orcamento`, recusa o serviço ou a peça excluída depois de incluída na OS com `ItemIndisponivel` (`422`), sem alterar nenhum item (issue #88). O mecânico remove o item antes de concluir o orçamento. As OS já orçadas continuam íntegras |
| Gerenciamento de dependências | `uv` com `pyproject.toml` e lockfile `uv.lock`. Comandos: `uv sync` (instala o ambiente), `uv add <pacote>` (adiciona dependência), `uv run pytest` (executa sem ativar o venv). A versão do uv é fixa em 0.8.22 (`required-version` no `pyproject.toml`), a mesma do Dockerfile e do CI: outra versão reescreve o `uv.lock` em outro formato (`revision`) e gera diffs e conflitos no lockfile |
| Imports a partir de `src/` | `PYTHONPATH=src`: `pythonpath = ["src"]` no pytest (`pyproject.toml`), `ENV PYTHONPATH=/app/src` no Dockerfile e `PYTHONPATH=src` no `.env` para a IDE |
| Lint e formatação | Ruff (`ruff check` e `ruff format`), configurado no `pyproject.toml` |
| Testes e cobertura | pytest + pytest-cov (RNF-12 a RNF-14) |
| Banco dos testes de integração | Banco `<POSTGRES_DB>_test` no mesmo container `db` do Compose, publicado em `127.0.0.1` pelo `docker-compose.testes.yml` (issue #28). Nenhuma dependência nova; os testes de integração exigem o banco no ar e, fora do CI, são pulados sem ele; no CI (`CI=true`), falham. As fixtures e os comandos estão na seção 5.7 |
| Migrations | Alembic com o template `async` (issue #4). A pasta `migrations/` e o `alembic.ini` ficam na raiz do projeto; cada mudança de schema é gerada com `uv run alembic revision --autogenerate -m "<descrição>"`, revisada antes do commit e aplicada com `alembic upgrade head` no `CMD` do Dockerfile, antes do Uvicorn (issue #25). O `migrations/env.py` é o ponto de montagem do Alembic e, por isso, é a exceção à regra de que só o `presentation/container.py` importa `infrastructure/config.py`: ele lê a configuração com `carregar_configuracao()` e cria a conexão com `criar_engine`. O `target_metadata` é o `Base.metadata` de `infrastructure/database/base.py`; cada modelo novo precisa ser importado no `env.py` para entrar no `--autogenerate`. A primeira revisão, `0001_schema_base`, é vazia; da `0002` à `0007` criam as tabelas `usuarios`, `clientes`, `servicos`, `veiculos`, `pecas` com `estoque_pecas` e as tabelas da OS. O autogenerate não compara triggers, então o trigger do histórico da OS, na `0007`, é coberto por um teste de integração próprio. Um teste de integração compara os modelos com o banco migrado e falha se faltar migration |
| Rate limiting | SlowAPI com contador em memória (RNF-05) |
| Rotas e DTOs | `presentation/routers/` e `presentation/schemas/`, um arquivo por recurso |
| Estrutura de pastas | Alinhada à seção 6 do modelo C4 (issue #9): `domain/events/`, `application/events/`, `application/handlers/`, `infrastructure/database/` e `presentation/middlewares/` (seções 2 e 3) |
| Configuração | `infrastructure/config.py` com pydantic-settings (issue #9). A configuração é lida e validada na subida da aplicação, nunca no import do módulo. Só o `presentation/container.py` importa o módulo, e os demais objetos recebem os valores pelo construtor |
| Ponto de entrada e montagem | `presentation/main.py` cria o app, registra os routers, declara o título, a versão, a descrição e o esquema Bearer JWT do OpenAPI (botão "Authorize" em `/docs`) e liga o ciclo de vida; `presentation/container.py` cria na subida a engine, a fábrica de sessões, o `JwtTokenService`, o `BcryptPasswordHasher` e o verificador do banco, e fecha a engine no encerramento (issues #9 e #26). Os casos de uso que alteram o saldo de peças recebem um `EventDispatcher` montado por requisição em `_eventos_da_requisicao`, e despacham os eventos dentro da unidade de trabalho; os handlers vêm de `app.state.fabricas_de_handlers` e são criados com a mesma sessão, para gravar na mesma transação (decisão "Despacho dos eventos na transação"; RF-12, RNF-08). Os handlers da reserva (RF-18), da alocação às OS com peça pendente (RF-19) e do estorno no cancelamento (RF-23) entram nessa lista. O `/health` vive em `routers/saude.py`, usa a porta `VerificadorDoBanco` e devolve `200` com o banco disponível e `503` sem ele. O container oferece `obter_autenticar_usuario`, que monta por requisição a unidade de trabalho, o `PostgresUsuarioRepository` e o caso de uso, e o `main.py` registra o router de login. Na subida, depois das migrations, o ciclo de vida chama `executar_carga_inicial`, que roda o caso de uso `CriarCargaInicial` (Gerente padrão e, com `SEED_DEMO=true`, os usuários de demonstração; usuário já existente é mantido como está) (RF-03) |
| CI (GitHub Actions) | `.github/workflows/ci.yml`, em cada PR e em cada push na `main` (issue #29): `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest` com PostgreSQL 16 e cobertura mínima de 80% em `domain/` e `application/` (`--cov-fail-under=80`), Bandit no `src/`, pip-audit nas dependências de produção, exportadas do `uv.lock` com hashes, e `docker build` da imagem. Usa o uv 0.8.22, a mesma versão do Dockerfile. As actions ficam fixadas pelo SHA do commit e atualizadas à mão, o job tem limite de 15 minutos, e só a execução de PR é cancelada por um push novo, para todo commit da `main` ter resultado. No CI (`CI=true`), os testes de integração falham em vez de serem pulados quando o banco não está disponível. As variáveis do workflow são valores de teste, sem segredo real (RNF-06) |
| Análise de vulnerabilidades (RNF-07) | pip-audit para as dependências, Bandit para o código-fonte e Trivy para a imagem Docker (issue #5). pip-audit e Bandit entram como dependências de desenvolvimento; o Trivy roda como binário separado ou pela imagem `aquasec/trivy`. Sem Dependabot. A análise roda sobre o commit final da entrega e o relatório vai para `docs/security/` |
| Teste de desempenho (RNF-10) | Locust, como dependência de desenvolvimento (issue #6). O relatório com o p95 é a evidência da medição; a falha automática quando o p95 passar de 500 ms precisa ser escrita no cenário |

### 8.2. Em Aberto

Os itens abaixo **ainda não foram decididos** pelo grupo. Não assuma uma escolha sem combinar antes; quando a decisão for tomada, mova o item para 8.1.

| Decisão | Opções levantadas e custos |
| :--- | :--- |
| Cenário do teste de desempenho (RNF-10) | O RNF-10 não define as "condições normais de operação local". Falta definir o número de usuários simultâneos, a duração do teste e as rotas medidas. |
| OS sem serviços nem peças | Hoje `finalizar_orcamento` aceita uma OS sem itens e gera um orçamento de R$ 0,00 (o RF-17 não diz nada). Opções: manter, ou recusar a conclusão do orçamento sem ao menos um item (nova exceção de regra de negócio, `422`). |
| Item excluído do catálogo antes do congelamento | Um serviço ou uma peça excluída depois de incluída na OS ainda é cotada no orçamento, porque o RF-11 e o RF-12 mantêm as OS existentes íntegras. Falta decidir se o orçamento deve recusar o item excluído. |
| Exceção da quantidade de peça | A regra "inteiro maior que zero" levanta `OrdemServicoInvalida` em `ItemPeca` e `QuantidadeInvalida` em `EstoquePeca`, `PendenciaPeca` e `AlocacaoPeca`. O objeto de valor `QuantidadePeca`, criado na issue #45 para os eventos, usa `QuantidadeInvalida`. Falta decidir se as quatro classes passam a validar por ele, com uma só exceção. |
| Token de usuário desativado ou rebaixado | O JWT vale por 24 h (RF-01) e é validado só pela assinatura e pela expiração. O usuário desativado não faz login, mas o token que já emitiu continua acessando as rotas até expirar, e um Gerente rebaixado continua agindo como Gerente. Dois Gerentes podem se desativar um ao outro com tokens antigos e deixar a oficina sem Gerente ativo. Opções: (A) conferir só o responsável nas rotas de escrita de `/usuarios`; (B) `obter_usuario_autenticado` consultar o banco e exigir usuário ativo e com o perfil atual, ao custo de 1 SELECT por requisição (RNF-10); (C) registrar a limitação. |
| Perfil Gerente no cadastro de usuários | O RF-03 diz que o Gerente cadastra "funcionários (Atendentes e Mecânicos)", mas `POST /usuarios` e `PUT /usuarios/{id}` aceitam também o perfil `GERENTE`. Falta decidir se o Gerente cria e promove outros Gerentes; conforme a resposta, o código ou o texto do RF-03 muda. |
| Cliente excluído que volta à oficina | O documento de um cliente excluído continua reservado (`DocumentoJaCadastrado`) e não há rota de reativação, então o cadastro do mesmo cliente responde `422`. O RF-04 e o RF-06 não definem a reativação. Opções: (A) o cadastro reativa o cliente excluído e aplica os dados novos; (B) rota `POST /clientes/{id}/reativar`, só para o Gerente; (C) registrar a limitação. |
| Prazo de reposição sem limite máximo | O `POST /pecas` aceita `prazo_reposicao_dias` até o maior `INTEGER`, mas a estimativa de entrega estoura o limite de datas a partir de cerca de 2,9 milhões de dias. Com uma peça assim pendente na OS, `estimar_entrega` levanta `OrdemServicoInvalida` e o detalhamento da OS responde `400`, o que a deixa ilegível; a consulta pública (RF-25) terá o mesmo efeito. Opções: (A) limitar o prazo no cadastro da peça; (B) devolver a estimativa nula quando ela estourar, em vez de recusar a consulta; (C) registrar a limitação. |
| Caractere NUL nos campos de texto | Um `\u0000` em `nome`, `email` ou `telefone` chega ao PostgreSQL, que o recusa, e a API responde `500` em vez de `400` ou `422`. O mesmo vale para os próximos cadastros. Proposta: um validador compartilhado pelos schemas, ou a recusa na validação de cada entidade. |

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
