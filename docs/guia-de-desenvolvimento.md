# Guia de Desenvolvimento

Este guia explica **onde colocar cada parte do código e como implementá-la** respeitando a arquitetura do projeto. Ele serve tanto para os desenvolvedores do grupo quanto para assistentes de IA: quem for implementar qualquer coisa deve ler este documento antes de criar ou alterar arquivos.

---

## 1. Fontes da Verdade

Antes de implementar, consulte os documentos abaixo. Em caso de conflito entre o código e a documentação, **a documentação prevalece**; se a documentação estiver errada, corrija-a no mesmo PR.

| Documento | O que define |
| :--- | :--- |
| `docs/requisitos-funcionais.md` | O que o sistema deve fazer (RF-01 a RF-17). |
| `docs/requisitos-nao-funcionais.md` | Arquitetura, segurança, banco, Docker e testes (RNF-01 a RNF-11). |
| `docs/ddd/linguagem-ubiqua.md` | Nomes oficiais do domínio e o mapeamento entre conceitos e código. |
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
│   └── repositories/     Portas (interfaces ABC) de persistência
├── application/      Orquestração dos casos de uso
│   ├── use_cases/        Um arquivo por caso de uso
│   └── ports/            Interfaces de serviços técnicos (token, hash de senha)
├── infrastructure/   Detalhes técnicos (banco, bibliotecas externas)
│   ├── repositories/     Implementações das portas de repositório (PostgreSQL)
│   └── security/         Implementações de JWT e hash de senha
└── presentation/     Entrada HTTP (rotas, DTOs, autenticação das rotas)
    ├── schemas.py        DTOs de entrada e saída
    └── auth/             Validação do token nas rotas
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
| `presentation` | `application`, `domain` (para tipos) e o framework web | Diretamente de `infrastructure`, exceto no ponto de montagem das dependências |

Se um caso de uso precisa de algo técnico (banco, token, hash), ele depende de uma **interface** (porta) e recebe a implementação pelo construtor. Nunca instancia a implementação diretamente.

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
| DTO de entrada ou saída da API | `src/presentation/` | `schemas.py` | `CriarOSRequest`, `OSResponse` |
| Validação de token nas rotas | `src/presentation/auth/` | `dependencies.py` | — |
| Teste unitário | `tests/unit/` | `test_<arquivo testado>.py` | `test_placa.py` |
| Teste de integração | `tests/integration/` | `test_<fluxo>.py` | `test_fluxo_aprovacao_orcamento.py` |
| Relatório de segurança | `docs/security/` | — | relatório da varredura (RNF-05) |

Se algo não se encaixa em nenhuma linha desta tabela, **não crie uma pasta nova por conta própria**: discuta com o grupo e, se aprovado, atualize esta tabela e `docs/estrutura-de-pastas.md` no mesmo PR.

---

## 4. Convenções

### 4.1. Nomes

* Use os termos da **Linguagem Ubíqua** em português: `OrdemServico`, `Cliente`, `Veiculo`, `Servico`, `Peca`, `Orcamento`, `StatusOS`. Não traduza para o inglês e não invente sinônimos (ex.: não use `Pedido` no lugar de `OrdemServico`).
* Identificadores sem acentos nem cedilha: `Veiculo`, `Peca`, `Orcamento`.
* Arquivos e funções em `snake_case`; classes em `PascalCase`; constantes em `UPPER_SNAKE_CASE`.
* Os valores de `StatusOS` são exatamente os do RF-13: `RECEBIDA`, `EM_DIAGNOSTICO`, `AGUARDANDO_APROVACAO`, `EM_EXECUCAO`, `FINALIZADA`, `ENTREGUE`, `CANCELADA`.

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
    def aprovar_orcamento(self) -> None:
        if self.status != StatusOS.AGUARDANDO_APROVACAO:
            raise TransicaoDeStatusInvalida(self.status, StatusOS.EM_EXECUCAO)
        self._mudar_status(StatusOS.EM_EXECUCAO)
```

Regras que **ficam obrigatoriamente no domínio**:
- Máquina de estados da OS e bloqueio de transições inválidas (RF-13).
- Registro do horário de cada transição (RF-14).
- Cálculo do orçamento: subtotal de serviços + soma de `quantidade × preço_unitario` das peças (RF-10).
- Validação de CPF, CNPJ e placa (RF-02, RF-04).

### 5.3. Criar uma Porta e um Adaptador de Repositório

1. Porta no domínio:

```python
# src/domain/repositories/cliente_repository.py
from abc import ABC, abstractmethod

from domain.entities.cliente import Cliente


class ClienteRepository(ABC):
    @abstractmethod
    def salvar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    def buscar_por_documento(self, documento: str) -> Cliente | None: ...
```

2. Adaptador na infraestrutura, herdando da porta:

```python
# src/infrastructure/repositories/postgres_cliente_repository.py
from domain.repositories.cliente_repository import ClienteRepository


class PostgresClienteRepository(ClienteRepository):
    ...
```

A porta recebe e devolve **entidades do domínio**, nunca modelos do ORM. A conversão entre entidade e tabela acontece dentro do adaptador.

### 5.4. Criar um Caso de Uso

Um arquivo por caso de uso. O caso de uso recebe as portas pelo construtor e expõe um único método `executar`.

```python
# src/application/use_cases/criar_os.py (trecho ilustrativo)
from domain.repositories.cliente_repository import ClienteRepository
from domain.repositories.ordem_servico_repository import OrdemServicoRepository


class CriarOS:
    def __init__(self, clientes: ClienteRepository, ordens: OrdemServicoRepository):
        self._clientes = clientes
        self._ordens = ordens

    def executar(self, documento_cliente: str, placa: str) -> OrdemServico:
        ...
```

O caso de uso **orquestra** (busca, chama métodos das entidades, salva). Se aparecer um `if` de regra de negócio no caso de uso, ele provavelmente deveria estar na entidade.

Operações que precisam ser **atômicas** (RNF-07): criação de OS com itens e baixa de estoque na aprovação do orçamento. Elas devem rodar dentro de uma única transação de banco; a aprovação deve impedir estoque negativo (RF-07).

### 5.5. Criar uma Rota HTTP

1. Defina os DTOs de entrada e saída em `src/presentation/schemas.py` (RNF-11).
2. A rota converte o DTO de entrada, chama o caso de uso e converte o resultado no DTO de saída.
3. A rota **não contém regra de negócio** e não acessa o repositório diretamente.
4. Use os códigos HTTP do RNF-11: `200`, `201`, `400`, `401`, `404`, `422`, `500`. Exceções do domínio são traduzidas para esses códigos na camada `presentation`.

### 5.6. Proteger uma Rota com JWT

* **Toda** rota administrativa e operacional exige token (RNF-03).
* A **única** rota pública é a consulta de status da OS pelo cliente (RF-15), identificada pelo número da OS junto com CPF/CNPJ ou placa.
* A validação do token e a checagem do perfil (Atendente, Mecânico, Administrador) ficam em `src/presentation/auth/dependencies.py`.
* O login é o caso de uso `application/use_cases/autenticar_usuario.py`, que usa as portas `TokenService` e `PasswordHasher`.
* Senhas são guardadas apenas como hash; a chave de assinatura do JWT vem de variável de ambiente (RNF-04).

### 5.7. Escrever Testes

| Tipo | Pasta | O que testa | Usa banco? |
| :--- | :--- | :--- | :--- |
| Unitário | `tests/unit/` | Entidades, objetos de valor e casos de uso | Não: use repositórios em memória que implementam a porta |
| Integração | `tests/integration/` | Fluxos completos, com adaptadores reais | Sim |

Exemplo de repositório em memória para testes unitários:

```python
class OrdemServicoRepositoryEmMemoria(OrdemServicoRepository):
    def __init__(self):
        self.dados = {}

    def salvar(self, os):
        self.dados[os.id] = os

    def buscar_por_id(self, id):
        return self.dados.get(id)
```

A cobertura deve ser de pelo menos **80%** nos domínios críticos (RNF-10). Todo código novo em `domain/` e `application/` deve vir acompanhado de testes.

---

## 6. Segurança

* Nunca commite senhas, chaves de JWT ou credenciais de banco (RNF-04). Use variáveis de ambiente.
* Senhas de usuário são armazenadas somente como hash.
* O relatório da varredura de vulnerabilidades vai em `docs/security/` (RNF-05).

---

## 7. Fluxo de Git

* Não faça commit direto na `main`. Crie uma branch e abra um PR.
* Nomes de branch: `<tipo>/<descricao-curta>`, por exemplo `feat/crud-clientes`, `fix/validacao-cnpj`, `chore/estrutura-conforme-docs`.
* Mensagens de commit em português, no formato `<tipo>: <descrição>`, com os tipos `feat`, `fix`, `chore`, `docs`, `test`, `refactor`.
* Sempre que possível, cite o requisito no corpo do commit ou no PR (ex.: "Implementa RF-04").

---

## 8. Decisões em Aberto

Os itens abaixo **ainda não foram decididos** pelo grupo. Não assuma uma escolha sem combinar antes; quando a decisão for tomada, atualize esta seção.

| Decisão | Situação |
| :--- | :--- |
| Framework web | Não definido. O nome `presentation/auth/dependencies.py` supõe FastAPI. |
| ORM ou acesso ao banco | Não definido. A documentação exige apenas PostgreSQL (RNF-06). |
| Biblioteca de JWT | Não definida. |
| Gerenciamento de dependências | Não definido (`pyproject.toml` ou `requirements.txt`). |
| Configuração do `PYTHONPATH` para os imports a partir de `src/` | Não definida. |
| Critério de aceite do RF-08 (abertura da OS) | Em branco na documentação. |

---

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
