# Requisitos Não Funcionais (RNF) - Sistema de Oficina Mecânica

Este documento especifica os **Requisitos Não Funcionais (RNF)** do MVP do sistema da oficina mecânica, definindo os atributos de qualidade, restrições arquiteturais, padrões de segurança, requisitos de desempenho e critérios de suporte à operação e deploy.

---

## 1. Arquitetura de Software e Design

### **RNF-01** - Monólito em Camadas

A solução deve ser implementada como uma arquitetura monolítica organizada em camadas claras (`presentation`, `application`, `domain`, `infrastructure`), garantindo o desacoplamento das regras de negócio.

### **RNF-02** - Isolamento do Domínio (DDD)

O núcleo de domínio (`domain`) deve ser totalmente isolado e independente de frameworks web, ORMs, bibliotecas de banco de dados ou detalhes de infraestrutura externa.

---

## 2. Segurança, Autenticação e Conformidade

### **RNF-03** - Autenticação de APIs Administrativas

Todas as rotas administrativas e operacionais devem ser protegidas por autenticação via JSON Web Token (JWT). Apenas endpoints públicos de consulta de status da OS por clientes devem ser abertos.

### **RNF-04** - Proteção de Credenciais e Segredos

Nenhuma senha de usuário, chave secreta de JWT ou credencial de banco de dados deve ser armazenada em texto plano ou comitada no repositório.

### **RNF-05** - Análise de Vulnerabilidades

O projeto deve passar por varredura automatizada de segurança de código/dependências, registrando o relatório técnico no repositório em `docs/security/`.

---

## 3. Persistência de Dados e Transacionalidade

### **RNF-06** - Banco de Dados Relacional

O armazenamento de dados deve utilizar banco relacional (PostgreSQL), garantindo suporte completo a transações ACID, integridade referencial e consistência do histórico de atendimentos.

### **RNF-07** - Atomicidade e Controle de Concorrência

As operações de criação de OS com itens e a baixa de peças no estoque durante a aprovação do orçamento devem ser executadas dentro de transações de banco atômicas. O sistema deve prevenir inconsistências de concorrência e estoque negativo.

---

## 4. Deploy e Containerização

### **RNF-08** - Containerização com Docker

A aplicação deve possuir um `Dockerfile` otimizado para build do serviço e um arquivo `docker-compose.yml` para orquestração completa do ambiente local (App + Banco PostgreSQL) executável com um único comando (`docker compose up`).

---

## 5. Qualidade de Software e Testes Automatizados

### **RNF-09** - Suíte de Testes Automatizados

O projeto deve conter testes unitários para entidades e objetos de valor do domínio, e testes de integração para validar os principais fluxos dos casos de uso de borda a borda.

### **RNF-10** - Cobertura Mínima de Código

A suíte de testes automatizados deve garantir uma cobertura de código (**code coverage**) igual ou superior a **80%** nos domínios críticos da aplicação.

---

## 6. Interoperabilidade e Documentação de API

### **RNF-11** - Padrão RESTful e DTOs

A API deve seguir os princípios RESTful, utilizando verbos HTTP adequados, tratamento padronizado de exceções, DTOs de entrada e saída e códigos de status HTTP apropriados (`200`, `201`, `400`, `401`, `404`, `422`, `500`).
