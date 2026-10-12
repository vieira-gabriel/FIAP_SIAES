# Linguagem Ubíqua e Glossário do Domínio (DDD)

Este documento estabelece a **Linguagem Ubíqua** do sistema de gestão da oficina mecânica, desenvolvida durante as sessões de Event Storming. A nomenclatura definida abaixo reflete o vocabulário oficial do negócio e possui correspondência direta com os pacotes, classes e modelos do código-fonte em Python.

---

## 1. Glossário e Termos do Domínio

| Termo do Negócio | Definição no Domínio | Correspondência no Código (`src/domain/`) |
| :--- | :--- | :--- |
| **Ordem de Serviço (OS)** | Entidade-raiz do agregado principal. Representa o documento e ciclo de vida completo do atendimento, consolidando cliente, veículo, mecânico, serviços, peças e orçamento. | `domain.entities.OrdemServico` |
| **Cliente** | Pessoa física ou jurídica proprietária do veículo e tomadora dos serviços da oficina. | `domain.entities.Cliente` |
| **Veículo** | Automóvel cadastrado no sistema vinculado a um cliente específico pela placa. | `domain.entities.Veiculo` |
| **Serviço** | Atividade técnica de manutenção ou reparo realizada pelos mecânicos (ex.: troca de óleo, alinhamento). | `domain.entities.Servico` |
| **Peça / Insumo** | Componente físico utilizado na manutenção com controle quantitativo de estoque (ex.: filtro de óleo, pastilha de freio). | `domain.entities.Peca` |
| **Orçamento** | Cálculo que consolida o valor congelado dos serviços solicitados e peças alocadas para aprovação do cliente. | `domain.value_objects.Orcamento` |
| **Estoque** | Agregado responsável pelo controle quantitativo físico, reserva temporária e baixa de peças. | `domain.entities.EstoquePeca` |

---

## 2. Objetos de Valor (Value Objects - VOs)

| Objeto de Valor | Regra e Validação do Domínio | Classe no Código |
| :--- | :--- | :--- |
| **CPF** | Identificador de cliente pessoa física com validação matemática rigorosa de dígitos verificadores. Imutável. | `domain.value_objects.CPF` |
| **CNPJ** | Identificador de cliente pessoa jurídica com validação matemática rigorosa de dígitos verificadores. Imutável. | `domain.value_objects.CNPJ` |
| **Placa** | Identificador de veículo compatível com formatos padrão antigo (`ABC1234`) e Padrão Mercosul (`ABC1D23`). | `domain.value_objects.Placa` |
| **Valor** | Representação numérica com precisão decimal adequada para valores financeiros e totais em reais. | `domain.value_objects.Valor` |
| **StatusOS** | Enumeração dos estados válidos do ciclo de vida da Ordem de Serviço. | `domain.value_objects.StatusOS` |

---

## 3. Perfis e Atores do Sistema (RBAC)

| Perfil / Ator | Função no Negócio | Escopo de Permissões na API |
| :--- | :--- | :--- |
| **Atendente** | Primeiro contato com o cliente e entrega final do veículo. | Criar, listar e atualizar OS; cadastrar e atualizar clientes/veículos; listar serviços; consultar e atualizar saldo de peças; alterar status para `ENTREGUE`. |
| **Mecânico** | Execução técnica, diagnóstico e reparo do veículo. | Listar e atualizar OS; atribuir-se a uma OS (`RECEBIDA` $\rightarrow$ `EM_DIAGNOSTICO`); adicionar serviços/peças e calcular orçamento (`AGUARDANDO_APROVACAO`); listar clientes e veículos; alterar status para `FINALIZADA`. |
| **Gerente (Admin)** | Gestão estratégica, administrativa e financeira da loja. | Acesso administrativo total (CRUD completo em todas as entidades: Criar, Listar, Atualizar e Deletar); forçar cancelamentos e alterar status em qualquer etapa; gerenciar catálogo de serviços e estoque; visualizar relatórios de tempo médio. |
| **Cliente** | Proprietário do veículo (Acesso público externo). | Consultar status da OS em tempo real via API pública (fornecendo Nº OS + CPF/CNPJ) e aprovar ou rejeitar orçamentos propostos. |

---

## 4. Contextos Delimitados (Bounded Contexts)

```
+--------------------------+     +--------------------------+
|  Identidade & Acesso     |     |   Atendimento & Cadastro |
|  (JWT / Perfis RBAC)     |     |   (Clientes e Veículos)  |
+--------------------------+     +--------------------------+
             |                                |
             +----------------+---------------|
                              |
                              v
             +----------------------------------+
             |     Ordem de Serviço (Core)      |
             |  (Lifecycle, Orçamento, Status)  |
             +----------------------------------+
                              |
             +----------------+---------------|
             |                                |
             v                                v
+--------------------------+     +--------------------------+
|      Estoque & Peças     |     |  Acompanhamento Público  |
|   (Reserva/Baixa Peças)  |     |   (Portal do Cliente)    |
+--------------------------+     +--------------------------+
```

---

## 5. Ciclo de Vida e Máquina de Estados da OS (`StatusOS`)

O coração do sistema é a máquina de estados da Ordem de Serviço. Apenas as transições mapeadas abaixo são permitidas pelo agregado `OrdemServico`:

1. **`RECEBIDA`**: OS aberta pelo Atendente com identificação do cliente e veículo.
2. **`EM_DIAGNOSTICO`**: Transição acionada quando o Mecânico se atribui à OS para avaliar o veículo e listar itens necessários.
3. **`AGUARDANDO_APROVACAO`**: Orçamento gerado com preços congelados; reserva temporária de peças acionada no estoque; disponibilizado no portal público do cliente.
4. **`EM_EXECUCAO`**: Cliente aprova o orçamento via portal público; baixa definitiva das peças confirmada e timestamp de início da execução gravado.
5. **`FINALIZADA`**: Mecânico conclui a manutenção técnica e grava o timestamp de término para medição do tempo médio.
6. **`ENTREGUE`**: Atendente realiza a entrega do veículo ao cliente após acerto comercial.
7. **`CANCELADA`**: Orçamento rejeitado pelo cliente ou cancelamento forçado pelo Gerente. Aciona a rotina automática de estorno de peças ao estoque.

---

## 6. Mapeamento Ubíquo De-Para (Documentação ↔ Código Python)

| Conceito da Documentação DDD | Elemento Arquitetural no Código Python | Exemplo no Repositório |
| :--- | :--- | :--- |
| **Entidade / Raiz de Agregado** | Classe de Domínio (`dataclass` pura) | `src/domain/entities/ordem_servico.py` |
| **Objeto de Valor (VO)** | Class / Dataclass Imutável | `src/domain/value_objects/cpf.py` |
| **Caso de Uso (Command Handler)** | Application Service | `src/application/use_cases/aprovar_orcamento.py` |
| **Porta de Repositório** | Interface Abstrata (`ABC`) | `src/domain/repositories/ordem_servico_repository.py` |
| **Adaptador de Infraestrutura** | Implementação ORM / SQL (`PostgreSQL`) | `src/infrastructure/repositories/postgres_ordem_servico_repository.py` |
| **Evento de Domínio** | Dataclass de Evento Imutável | `src/domain/events/orcamento_aprovado_event.py` |
