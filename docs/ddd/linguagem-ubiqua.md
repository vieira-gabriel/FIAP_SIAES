# Linguagem Ubíqua e Glossário do Domínio (DDD)

Este documento estabelece a **Linguagem Ubíqua** do sistema de gestão da oficina mecânica, desenvolvida durante as sessões de Event Storming. A nomenclatura definida abaixo reflete o vocabulário oficial do negócio e possui correspondência direta com os pacotes, classes e modelos do código-fonte em Python.

---

## 1. Glossário e Termos do Domínio

| Termo do Negócio | Definição no Domínio | Correspondência no Código (`src/domain/`) |
| :--- | :--- | :--- |
| **Ordem de Serviço (OS)** | Entidade-raiz do agregado principal. Representa o documento e ciclo de vida completo do atendimento, consolidando cliente, veículo, mecânico, serviços, peças e orçamento. | `domain.entities.OrdemServico` |
| **Número da OS** | Identificador da OS informado ao cliente: 3 primeiros dígitos do CPF/CNPJ do cliente, hífen e 8 primeiros caracteres hexadecimais do UUID interno (ex.: `123-7F3A9C2B`). Usado junto com o CPF/CNPJ na consulta pública. | `domain.value_objects.NumeroOS` |
| **Cliente** | Pessoa física ou jurídica proprietária do veículo e tomadora dos serviços da oficina. | `domain.entities.Cliente` |
| **Veículo** | Automóvel cadastrado no sistema vinculado a um cliente específico pela placa. | `domain.entities.Veiculo` |
| **Serviço** | Atividade técnica de manutenção ou reparo realizada pelos mecânicos (ex.: troca de óleo, alinhamento), com valor base e tempo estimado de execução. | `domain.entities.Servico` |
| **Peça / Insumo** | Componente físico utilizado na manutenção com controle quantitativo de estoque (ex.: filtro de óleo, pastilha de freio), com prazo de reposição. | `domain.entities.Peca` |
| **Orçamento** | Cálculo que consolida o valor congelado dos serviços solicitados e peças alocadas para aprovação do cliente. | `domain.value_objects.Orcamento` |
| **Estoque** | Agregado responsável pelo controle quantitativo físico, reserva temporária e baixa de peças. | `domain.entities.EstoquePeca` |
| **Reserva** | Quantidade de uma peça separada para uma OS a partir da conclusão do orçamento. Reduz o saldo disponível sem reduzir a quantidade física. | Quantidade reservada em `ItemPeca` e `EstoquePeca` |
| **Peça Pendente** | Quantidade de uma peça da OS que não pôde ser reservada por falta de saldo. É alocada automaticamente quando o estoque é reposto, com prioridade para a OS mais antiga. | Quantidade pendente em `ItemPeca` |
| **Baixa** | Saída definitiva das peças reservadas do estoque, executada no início da execução da OS. | Método de `EstoquePeca` |
| **Estorno** | Devolução das quantidades reservadas ao saldo disponível quando o orçamento é rejeitado ou a OS é cancelada. Peças já baixadas não são estornadas. | Método de `EstoquePeca` |
| **Histórico de Status** | Registro imutável de cada transição de status da OS, com status anterior, novo status, data/hora, origem, usuário e motivo. | `domain.entities.HistoricoStatusOS` |
| **Estimativa de Entrega** | Data prevista de conclusão exibida ao cliente, calculada pela soma dos tempos estimados dos serviços e pelo prazo de reposição das peças pendentes. | Método de `OrdemServico` |
| **Usuário** | Funcionário interno da oficina com acesso autenticado ao sistema (Atendente, Mecânico ou Gerente). Guarda apenas o hash da senha e pode ser desativado pelo Gerente; usuário desativado não faz login. O cliente não é um usuário. | `domain.entities.Usuario` |

---

## 2. Objetos de Valor (Value Objects - VOs)

| Objeto de Valor | Regra e Validação do Domínio | Classe no Código |
| :--- | :--- | :--- |
| **CPF** | Identificador de cliente pessoa física com validação matemática rigorosa de dígitos verificadores. Imutável. | `domain.value_objects.CPF` |
| **CNPJ** | Identificador de cliente pessoa jurídica com validação matemática rigorosa de dígitos verificadores. Imutável. | `domain.value_objects.CNPJ` |
| **Placa** | Identificador de veículo compatível com formatos padrão antigo (`ABC1234`) e Padrão Mercosul (`ABC1D23`). | `domain.value_objects.Placa` |
| **Valor** | Representação numérica com precisão decimal adequada para valores financeiros e totais em reais. | `domain.value_objects.Valor` |
| **NumeroOS** | Número da OS no formato `DDD-XXXXXXXX` (3 dígitos do documento e 8 caracteres hexadecimais maiúsculos). Imutável. | `domain.value_objects.NumeroOS` |
| **StatusOS** | Enumeração dos estados válidos do ciclo de vida da Ordem de Serviço. | `domain.value_objects.StatusOS` |
| **OrigemTransicao** | Enumeração de quem provocou uma transição de status: `USUARIO`, `CLIENTE` ou `SISTEMA`. | `domain.value_objects.OrigemTransicao` |
| **PerfilUsuario** | Enumeração dos perfis de acesso dos usuários internos: `ATENDENTE`, `MECANICO` ou `GERENTE`. É o valor da claim `role` do token JWT. | `domain.value_objects.PerfilUsuario` |

---

## 3. Perfis e Atores do Sistema (RBAC)

| Perfil / Ator | Função no Negócio | Escopo de Permissões na API |
| :--- | :--- | :--- |
| **Atendente** | Primeiro contato com o cliente e entrega final do veículo. | Criar, listar, detalhar e atualizar OS; cadastrar e atualizar clientes/veículos; listar serviços; consultar peças; alterar status para `ENTREGUE`. |
| **Mecânico** | Execução técnica, diagnóstico e reparo do veículo. | Listar, detalhar e atualizar OS; atribuir-se a uma OS (`RECEBIDA` $\rightarrow$ `EM_DIAGNOSTICO`); adicionar serviços/peças e concluir orçamento (`AGUARDANDO_APROVACAO`); iniciar a execução das OS atribuídas a ele (`EM_EXECUCAO`); listar clientes e veículos; consultar e atualizar saldo de peças; alterar status para `FINALIZADA`. |
| **Gerente (Admin)** | Gestão estratégica, administrativa e financeira da loja. | Acesso administrativo total (CRUD completo em todas as entidades: Criar, Listar, Atualizar e Deletar); cancelar OS com motivo; gerenciar catálogo de serviços e estoque; visualizar relatórios de tempos médios. |
| **Cliente** | Proprietário do veículo (Acesso público externo). | Consultar status da OS em tempo real via API pública (fornecendo Nº OS + CPF/CNPJ) e aprovar ou rejeitar orçamentos propostos. |
| **Sistema** | Automação de domínio, sem usuário associado. | Reservar e estornar peças; alocar peças repostas às OS pendentes; liberar OS de `AGUARDANDO_PECA` para `AGUARDANDO_EXECUCAO`. |

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

O coração do sistema é a máquina de estados da Ordem de Serviço. O enunciado define seis status; o sistema acrescenta `AGUARDANDO_PECA`, `AGUARDANDO_EXECUCAO` e `CANCELADA` (justificativa na seção 5 de `docs/requisitos-funcionais.md`).

1. **`RECEBIDA`**: OS aberta pelo Atendente com identificação do cliente e veículo.
2. **`EM_DIAGNOSTICO`**: Transição acionada quando o Mecânico se atribui à OS para avaliar o veículo e listar itens necessários.
3. **`AGUARDANDO_APROVACAO`**: Orçamento gerado com preços congelados; reserva das peças com saldo e registro das peças pendentes; disponibilizado no portal público do cliente.
4. **`AGUARDANDO_PECA`**: Cliente aprovou o orçamento, mas ainda há peças pendentes; a OS espera a reposição do estoque.
5. **`AGUARDANDO_EXECUCAO`**: Orçamento aprovado e todas as peças reservadas; a OS espera o mecânico iniciar o serviço.
6. **`EM_EXECUCAO`**: Mecânico iniciou o serviço; baixa definitiva das peças e timestamp de início da execução gravado.
7. **`FINALIZADA`**: Mecânico conclui a manutenção técnica e grava o timestamp de término para medição do tempo médio.
8. **`ENTREGUE`**: Atendente realiza a entrega do veículo ao cliente após acerto comercial. Estado final.
9. **`CANCELADA`**: Orçamento rejeitado pelo cliente ou cancelamento pelo Gerente. Estorna as reservas ao estoque. Estado final.

Apenas as transições abaixo são permitidas pelo agregado `OrdemServico`; qualquer outra é bloqueada:

| De | Para | Ação (método do agregado) | Quem executa | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| - | `RECEBIDA` | Abrir OS | Atendente, Gerente | RF-13 |
| `RECEBIDA` | `EM_DIAGNOSTICO` | `atribuir_mecanico` | Mecânico, Gerente | RF-16 |
| `EM_DIAGNOSTICO` | `AGUARDANDO_APROVACAO` | `finalizar_orcamento` | Mecânico, Gerente | RF-17, RF-18 |
| `AGUARDANDO_APROVACAO` | `AGUARDANDO_EXECUCAO` | `aprovar_orcamento` (sem peças pendentes) | Cliente | RF-26 |
| `AGUARDANDO_APROVACAO` | `AGUARDANDO_PECA` | `aprovar_orcamento` (com peças pendentes) | Cliente | RF-26 |
| `AGUARDANDO_APROVACAO` | `CANCELADA` | `rejeitar_orcamento` | Cliente | RF-26, RF-18 |
| `AGUARDANDO_PECA` | `AGUARDANDO_EXECUCAO` | `liberar_para_execucao` | Sistema | RF-19 |
| `AGUARDANDO_EXECUCAO` | `EM_EXECUCAO` | `iniciar_execucao` | Mecânico atribuído, Gerente | RF-20 |
| `EM_EXECUCAO` | `FINALIZADA` | `concluir_manutencao` | Mecânico, Gerente | RF-21 |
| `FINALIZADA` | `ENTREGUE` | `entregar_veiculo` | Atendente, Gerente | RF-22 |
| `RECEBIDA` a `EM_EXECUCAO` | `CANCELADA` | `cancelar(motivo)` | Gerente | RF-23, RF-18 |

Toda transição gera um registro no Histórico de Status (RF-24).

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
