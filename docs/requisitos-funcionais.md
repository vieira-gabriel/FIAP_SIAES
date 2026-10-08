# Requisitos Funcionais (RF) - Sistema de Oficina Mecânica

Este documento especifica todos os **Requisitos Funcionais (RF)** do MVP do sistema de gestão da oficina mecânica, definindo o que o sistema deve executar para atender aos fluxos de negócio de atendimento, diagnóstico, orçamentação, execução e acompanhamento de serviços.

---

## 1. Gestão de Clientes

### **RF-01** - CRUD de Clientes

O sistema deve permitir o cadastramento, consulta, atualização e remoção lógica de clientes (pessoas físicas e jurídicas).

#### Critério de Aceite / Validação

Permitir registrar nome/razão social, e-mail, telefone e documento oficial (CPF ou CNPJ).

### **RF-02** - Validação de Documento

O sistema deve validar matematicamente os números de CPF e CNPJ no momento do cadastro ou identificação.

#### Critério de Aceite / Validação

Rejeitar documentos com tamanho inválido ou com dígitos verificadores incorretos.

---

## 2. Gestão de Veículos

### **RF-03** - CRUD de Veículos 

O sistema deve permitir o cadastro e vinculação de veículos aos seus respectivos proprietários (clientes).

#### Critério de Aceite / Validação

Cada veículo deve conter dados de placa, marca, modelo e ano de fabricação.


### **RF-04** - Validação de Placa

O sistema deve validar o formato da placa do veículo, aceitando tanto o padrão nacional antigo quanto o padrão Mercosul.

#### Critério de Aceite / Validação

Aceitar placas nos padrões `ABC1234` (antigo) e `ABC1D23` (Mercosul).

---

## 3. Gestão de Serviços

### **RF-05** - CRUD de Serviços

O sistema deve manter o catálogo de serviços oferecidos pela oficina mecanizada (ex.: troca de óleo, alinhamento, balanceamento, alinhamento de direção).

#### Critério de Aceite / Validação

Registrar nome do serviço, descrição técnica e valor base do serviço.

---

## 4. Gestão de Peças e Insumos (Estoque)

### **RF-06** - CRUD de Peças

O sistema deve permitir o cadastro e gerenciamento das peças e insumos utilizados nas manutenções.

#### Critério de Aceite / Validação

Registrar nome do item, código de referência, preço unitário de venda e quantidade em estoque.

### **RF-07**  - Controle de Estoque

O sistema deve controlar as entradas e saídas de estoque de cada peça/insumo.

#### Critério de Aceite / Validação

Impedir a aprovação de ordens de serviço caso a quantidade de peças necessárias seja superior ao estoque disponível.

---

## 5. Criação e Gestão da Ordem de Serviço (OS)

### **RF-08** - Abertura da OS

O sistema deve permitir criar uma nova Ordem de Serviço identificando o cliente por CPF/CNPJ e vinculando o veículo correspondente.

#### Critério de Aceite / Validação

?

### **RF-09**  - Composição de Itens da OS

O sistema deve permitir a inclusão e exclusão de múltiplos serviços e peças/insumos em uma OS.

#### Critério de Aceite / Validação

Cada item de peça deve registrar a quantidade solicitada e o valor unitário praticado no momento.

### **RF-10**  - Geração Automática do Orçamento

O sistema deve calcular automaticamente o valor total do orçamento da OS.

#### Critério de Aceite / Validação

Somatório exato do subtotal de serviços + subtotal de peças (`quantidade × preço_unitario`).

### **RF-11** - Envio e Disponibilização do Orçamento

O sistema deve gerar a proposta de orçamento e disponibilizá-la ao cliente para apreciação.

#### Critério de Aceite / Validação

A OS transita para o status `AGUARDANDO_APROVACAO` com o detalhamento dos valores.

### **RF-12** - Aprovação / Rejeição do Orçamento

O sistema deve registrar a decisão do cliente sobre o orçamento submetido.

#### Critério de Aceite / Validação

Se **aprovado**, transita para `EM_EXECUCAO` e efetua a baixa automática de peças no estoque. Se **rejeitado**, transita para `CANCELADA`.

---

## 6. Acompanhamento e Ciclo de Vida da OS

### **RF-13** - Máquina de Estados da OS

O sistema deve gerenciar estritamente os status da OS: `RECEBIDA`, `EM_DIAGNOSTICO`, `AGUARDANDO_APROVACAO`, `EM_EXECUCAO`, `FINALIZADA`, `ENTREGUE` e `CANCELADA`.

#### Critério de Aceite / Validação

Transições inválidas (ex.: tentar passar de `RECEBIDA` diretamente para `FINALIZADA`) devem ser bloqueadas pelo domínio.

## **RF-14** - Transição Automática de Status

O sistema deve alterar o status da OS automaticamente conforme ações executadas nos casos de uso.

#### Critério de Aceite / Validação

Registrar timestamps em cada transição para auditoria e histórico de ciclo de vida.


### **RF-15** - Consulta Pública pelo Cliente

O sistema deve disponibilizar um endpoint público (sem necessidade de login) para que o cliente consulte o status atual do serviço.

#### Critério de Aceite / Validação

A busca deve ser feita mediante identificação (ex.: Número da OS + CPF/CNPJ ou Placa), retornando status, resumo e previsão.

---

## 7. Gestão Administrativa e Métricas

### **RF-16** - Listagem e Detalhamento de OS

O sistema deve permitir aos administradores e mecânicos listar e filtrar Ordens de Serviço por status, cliente, período ou placa.

#### Critério de Aceite / Validação

Exibir visualização detalhada com histórico completo, cliente, veículo, itens e valores.

### **RF-17** - Monitoramento do Tempo Médio de Execução

O sistema deve calcular o tempo médio de execução dos serviços finalizados.

#### Critério de Aceite / Validação

Cálculo baseado no intervalo entre o timestamp de início da execução (`EM_EXECUCAO`) e a conclusão técnica (`FINALIZADA`).
