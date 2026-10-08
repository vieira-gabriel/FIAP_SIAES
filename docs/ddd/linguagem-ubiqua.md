# Linguagem Ubíqua e Glossário do Domínio (DDD)

Este documento estabelece a **Linguagem Ubíqua** do sistema de gestão da oficina mecânica, desenvolvida durante as sessões de Event Storming. A nomenclatura definida abaixo reflete o vocabulário oficial do negócio e possui correspondência direta com os pacotes, classes e modelos do código-fonte em Python.

---

## 1. Glossário e Termos do Domínio

| Termo do Negócio | Definição no Domínio | Correspondência no Código (`src/domain/`) |
| :--- | :--- | :--- |
| **Ordem de Serviço (OS)** | Entidade-raiz do agregado principal. Representa o documento e ciclo de vida completo do atendimento, consolidando cliente, veículo, serviços, peças e orçamento. | `domain.entities.OrdemServico` |
| **Cliente** | Pessoa física ou jurídica proprietária do veículo e tomadora dos serviços da oficina. | `domain.entities.Cliente` |
| **Veículo** | Automóvel cadastrado no sistema vinculado a um cliente específico pela placa. | `domain.entities.Veiculo` |
| **Serviço** | Atividade técnica de manutenção ou reparo realizada pelos mecânicos (ex.: troca de óleo, alinhamento). | `domain.entities.Servico` |
| **Peça / Insumo** | Componente físico utilizado na manutenção com controle quantitativo de estoque (ex.: filtro de óleo, pastilha de freio). | `domain.entities.Peca` |
| **Orçamento** | Cálculo automático que consolida o valor total dos serviços solicitados e peças alocadas para aprovação do cliente. | `domain.value_objects.Orcamento` |

---

## 2. Objetos de Valor (Value Objects - VOs)

| Objeto de Valor | Regra e Validação do Domínio | Classe no Código |
| :--- | :--- | :--- |
| **CPF** | Identificador de cliente pessoa física com validação matemática rigorosa de dígitos verificadores. Imutável. | `domain.value_objects.CPF` |
| **CNPJ** | Identificador de cliente pessoa jurídica com validação matemática rigorosa de dígitos verificadores. Imutável. | `domain.value_objects.CNPJ` |
| **Placa** | Identificador de veículo compatível com formatos padrão antigo (`ABC1234`) e Padrão Mercosul (`ABC1D23`). | `domain.value_objects.Placa` |
| **Valor** | Representação numérica com precisão decimal adequada para valores financeiros e totais em real. | `domain.value_objects.Valor` |
| **StatusOS** | Enumeração dos estados válidos do ciclo de vida da Ordem de Serviço. | `domain.value_objects.StatusOS` |

---

## 3. Atores do Sistema

| Ator | Papel no Sistema | Escopo de Acesso |
| :--- | :--- | :--- |
| **Cliente** | Proprietário do veículo | Consulta pública de status da OS e aprovação/rejeição de orçamentos. |
| **Atendente** | Operador da recepção da oficina | Abertura de OS, cadastro de clientes e veículos, entrega do veículo. |
| **Mecânico** | Executor da manutenção | Diagnóstico, inclusão de serviços/peças e execução da OS. |
| **Administrador** | Gestor da oficina | Gestão de catálogo de serviços, controle de estoque e relatórios. |

---

## 4. Mapeamento Ubíquo De-Para (Documentação ↔ Código)

| Conceito da Documentação DDD | Elemento Arquitetural no Código Python | Exemplo no Repositório |
| :--- | :--- | :--- |
| **Entidade / Raiz de Agregado** | Classe de Domínio (Pure Python) | `src/domain/entities/ordem_servico.py` |
| **Objeto de Valor (VO)** | Dataclass / Class Imutável | `src/domain/value_objects/cpf_cnpj.py` |
| **Caso de Uso (Command Handler)** | Application Service | `src/application/use_cases/criar_os.py` |
| **Porta de Repositório** | Interface Abstrata (ABC) | `src/domain/repositories/ordem_servico_repository.py` |
| **Adaptador de Infraestrutura** | Implementação ORM / SQL (PostgreSQL) | `src/infrastructure/repositories/postgres_ordem_servico_repository.py` |
