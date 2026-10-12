# Requisitos Funcionais (RF) - Sistema de Oficina Mecânica

Este documento especifica todos os **Requisitos Funcionais (RF)** do MVP do sistema de gestão da oficina mecânica, estabelecendo as regras de negócio operacionais para as duas frentes do sistema: a **Frente da Loja** (acesso autenticado e controlado por perfis - RBAC) e a **Frente do Cliente** (acompanhamento público desautenticado e seguro).

---

## Matriz de Perfis e Permissões de Acesso (RBAC)

O acesso às funcionalidades da aplicação é estritamente controlado com base nos seguintes perfis:

* **`Atendente`**: Responsável pelo primeiro contato, cadastro de clientes/veículos, abertura de OS, consulta de serviços/peças e entrega final do veículo.
* **`Mecânico`**: Responsável pela avaliação técnica, diagnóstico, inclusão de itens/peças na OS, cálculo de orçamento e execução da manutenção.
* **`Gerente` (Admin)**: Administrador com privilégios totais (CRUD completo em todas as entidades, gerenciamento de usuários/credenciais internas, cancelamentos forçados, gestão de catálogo e relatórios de métricas/SLA).
* **`Cliente` (Público)**: Acesso público desautenticado restrito à consulta de status da própria OS e aprovação/rejeição do orçamento proposto.

---

## 1. Autenticação e Gestão de Usuários Internos (RBAC)

##### **RF-01** - Autenticação de Usuários Internos via JWT
###### Descrição do Domínio
O sistema deve autenticar usuários da equipe interna da loja (Atendentes, Mecânicos e Gerentes) emitindo um token JWT assinado digitalmente contendo a *claim* de perfil (`role`) e tempo de expiração padrão de 1 dia (24 horas).
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Exigir login com e-mail e senha cadastrados.
* Retornar o token JWT com tempo de expiração de 24 horas.
* Rejeitar acessos a rotas administrativas sem token válido com código HTTP `401 Unauthorized`.

##### **RF-02** - Controle de Acesso Baseado em Perfis (RBAC)
###### Descrição do Domínio
O sistema deve interceptar cada requisição administrativa e validar se o perfil contido no token JWT possui autorização para executar a ação solicitada.
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Se o perfil do token não possuir permissão para a rota, o sistema deve bloquear a requisição e retornar HTTP `403 Forbidden`.

##### **RF-03** - Gestão de Usuários Internos e Carga Inicial (Seed Data)
###### Descrição do Domínio
O sistema deve permitir que o Gerente cadastre, consulte, atualize e desative acessos de funcionários (Atendentes e Mecânicos). Adicionalmente, na inicialização da aplicação, o sistema deve executar um script de carga inicial (*seed data*) criando o usuário administrador padrão (`admin@oficina.com`).
###### Perfis de Acesso
`Gerente` (Acesso Exclusivo)
###### Critério de Aceite / Validação
* Apenas o perfil Gerente pode criar novas contas de funcionários e definir seus perfis (`role`).
* Armazenar senhas exclusivamente na forma de hash criptográfico (ex.: bcrypt).
* Executar a criação automatizada do usuário Gerente padrão via *seed data* no banco de dados na subida do container.

---

## 2. Gestão de Clientes (Frente da Loja)

##### **RF-04** - Cadastro e Identificação de Clientes
###### Descrição do Domínio
O sistema deve permitir o cadastramento e identificação de clientes (pessoas físicas ou jurídicas). Caso o cliente já exista no banco de dados, seus dados devem ser carregados automaticamente durante a abertura da OS.
###### Perfis de Acesso
`Atendente`, `Gerente` (Cadastro/Atualização/Listagem) | `Mecânico` (Apenas Listagem/Consulta)
###### Critério de Aceite / Validação
* Permitir registrar nome/razão social, e-mail, telefone e documento oficial (CPF ou CNPJ).

##### **RF-05** - Validação de Documentos de Clientes (CPF / CNPJ)
###### Descrição do Domínio
O sistema deve validar matematicamente os números de CPF e CNPJ antes de registrar ou atualizar qualquer cliente.
###### Perfis de Acesso
`Atendente`, `Gerente`
###### Critério de Aceite / Validação
* Rejeitar documentos com tamanho inválido ou com dígitos verificadores incorretos via Value Object imutável de domínio.

##### **RF-06** - Exclusão de Clientes
###### Descrição do Domínio
O sistema deve permitir a remoção de registros de clientes do cadastro.
###### Perfis de Acesso
`Gerente` (Exclusividade de administração)
###### Critério de Aceite / Validação
* Permitir a exclusão lógica apenas ao perfil Gerente, preservando o histórico de ordens de serviço já finalizadas.

---

## 3. Gestão de Veículos (Frente da Loja)

##### **RF-07** - Cadastro e Vínculo de Veículos
###### Descrição do Domínio
O sistema deve permitir cadastrar e atualizar veículos vinculados a um cliente proprietário. Na abertura da OS, se o veículo já estiver cadastrado, os dados são carregados automaticamente; caso contrário, permite-se o cadastro do novo veículo no mesmo fluxo.
###### Perfis de Acesso
`Atendente`, `Gerente` (Cadastro/Atualização/Listagem) | `Mecânico` (Apenas Listagem/Consulta)
###### Critério de Aceite / Validação
* Registrar placa, marca, modelo e ano de fabricação vinculados ao ID do cliente proprietário.

##### **RF-08** - Validação de Formato de Placa
###### Descrição do Domínio
O sistema deve validar o formato da placa do veículo, aceitando tanto o padrão antigo quanto o Padrão Mercosul.
###### Perfis de Acesso
`Atendente`, `Gerente`
###### Critério de Aceite / Validação
* Validar placas nos padrões `ABC1234` (antigo) e `ABC1D23` (Mercosul).

##### **RF-09** - Exclusão de Veículos
###### Descrição do Domínio
O sistema deve permitir a exclusão de veículos cadastrados.
###### Perfis de Acesso
`Atendente`, `Gerente`
###### Critério de Aceite / Validação
* Permitir a exclusão lógica apenas aos perfis Atendente e Gerente, preservando o histórico de ordens de serviço já finalizadas.

---

## 4. Gestão do Catálogo de Serviços e Estoque de Peças

##### **RF-10** - Consulta e Listagem do Catálogo de Serviços
###### Descrição do Domínio
O sistema deve disponibilizar a listagem e consulta dos serviços oferecidos pela oficina e seus respectivos valores base.
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Retornar código, nome do serviço, descrição técnica e valor base do serviço.

##### **RF-11** - Administração do Catálogo de Serviços (CRUD Amplo)
###### Descrição do Domínio
O sistema deve permitir criar novos serviços, alterar valores base e excluir serviços do catálogo.
###### Perfis de Acesso
`Gerente`
###### Critério de Aceite / Validação
* Apenas o Gerente pode cadastrar, editar preços base ou remover serviços do catálogo.

##### **RF-12** - Gestão de Peças e Controle de Estoque
###### Descrição do Domínio
O sistema deve permitir a consulta, cadastro, atualização do saldo e baixa de peças e insumos. Atendentes e Mecânicos podem listar e atualizar saldos operacionais de peças; a criação de novos itens e exclusão são restritas à gerência.
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente` (Listar e Atualizar Estoque) | `Gerente` (Criar e Deletar Peças)
###### Critério de Aceite / Validação
* Controlar quantidade física disponível, preço unitário de venda e código de referência da peça.

---

## 5. Ciclo de Vida e Abertura da Ordem de Serviço (OS)

##### **RF-13** - Abertura de Ordem de Serviço
###### Descrição do Domínio
O sistema deve permitir a criação de uma nova Ordem de Serviço associando cliente e veículo cadastrados. A OS é criada com o status inicial `RECEBIDA`.
###### Perfis de Acesso
`Atendente`, `Gerente`
###### Critério de Aceite / Validação
* Gerar um identificador único de OS, gravar data/hora de abertura e definir o status inicial como `RECEBIDA`.

##### **RF-14** - Atribuição de Mecânico e Início de Diagnóstico
###### Descrição do Domínio
O sistema deve permitir que o mecânico assuma a OS, vinculando seu ID à Ordem de Serviço. No momento da vinculação, a OS muda automaticamente de `RECEBIDA` para `EM_DIAGNOSTICO`.
###### Perfis de Acesso
`Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* O status deve alterar para `EM_DIAGNOSTICO` imediatamente ao atribuir o ID do mecânico responsável.

##### **RF-15** - Inclusão de Itens e Congelamento de Preços no Orçamento
###### Descrição do Domínio
O sistema deve permitir incluir serviços e peças na OS durante a fase de diagnóstico. Ao calcular o orçamento, o sistema busca os valores vigentes dos serviços e peças e congela estes valores na OS, garantindo que reajustes futuros no catálogo não alterem o valor cotado.
###### Perfis de Acesso
`Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* O cálculo do orçamento é a soma exata dos valores congelados dos serviços e peças incluídos.
* Ao concluir o orçamento, a OS muda para `AGUARDANDO_APROVACAO`.

##### **RF-16** - Reserva Temporária e Estorno Automático de Estoque
###### Descrição do Domínio
O sistema deve realizar a reserva temporária das peças no estoque no momento em que a OS transita para `AGUARDANDO_APROVACAO`. Caso o cliente rejeite o orçamento ou a OS seja cancelada, o sistema deve executar uma rotina automática para desalocar e estornar as peças ao estoque.
###### Perfis de Acesso
`Sistema` (Automação de Domínio / Event Dispatcher)
###### Critério de Aceite / Validação
* Em caso de rejeição/cancelamento, o saldo reservado deve ser devolvido ao estoque sem intervenção manual.

##### **RF-17** - Execução da OS e Registro de Timestamp de Início
###### Descrição do Domínio
Com a aprovação do orçamento, a OS muda para `EM_EXECUCAO`, confirmando a baixa das peças e gravando o timestamp exato do início da execução do serviço.
###### Perfis de Acesso
`Sistema` / `Mecânico`
###### Critério de Aceite / Validação
* Gravar o timestamp inicial obrigatório para o cálculo posterior do tempo médio de execução.

##### **RF-18** - Conclusão da Manutenção e Registro de Timestamp de Término
###### Descrição do Domínio
O mecânico deve sinalizar a conclusão técnica da manutenção, alterando o status da OS de `EM_EXECUCAO` para `FINALIZADA` e gravando o timestamp final.
###### Perfis de Acesso
`Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Gravar o timestamp final e impedir novas alterações de itens na OS.

##### **RF-19** - Entrega do Veículo ao Cliente
###### Descrição do Domínio
Após a conclusão técnica e acerto comercial, o atendente altera o status da OS de `FINALIZADA` para `ENTREGUE`. Esta transição é de responsabilidade exclusiva da equipe de atendimento.
###### Perfis de Acesso
`Atendente`, `Gerente`
###### Critério de Aceite / Validação
* Apenas Atendentes e Gerentes podem realizar a mudança de status para `ENTREGUE`. Mecânicos não possuem permissão para esta transição.

##### **RF-20** - Cancelamento Forçado e Alteração Excepcional de Status
###### Descrição do Domínio
O sistema deve permitir que o Gerente cancele uma OS ou force a alteração de status em qualquer etapa do fluxo em situações excepcionais de loja.
###### Perfis de Acesso
`Gerente` (Acesso Exclusivo)
###### Critério de Aceite / Validação
* Registrar o motivo do cancelamento forçado no histórico de auditoria da OS.

---

## 6. Acompanhamento Público e Segurança do Cliente (Frente do Cliente)

##### **RF-21** - Consulta Pública de Status da OS
###### Descrição do Domínio
O sistema deve disponibilizar um endpoint público (sem exigência de JWT) permitindo que o cliente consulte o status em tempo real da sua OS fornecendo obrigatoriamente a combinação do **Número da OS + CPF/CNPJ** do titular.
###### Perfis de Acesso
`Cliente` (Acesso Público Desautenticado)
###### Critério de Aceite / Validação
* Retornar o status atual, descrição resumida dos serviços, valor total do orçamento e estimativa de entrega.
* Ocultar dados pessoais sensíveis do cliente e custos internos de fornecedores.

##### **RF-22** - Aprovação ou Rejeição de Orçamento pelo Cliente
###### Descrição do Domínio
O sistema deve permitir que o cliente aprove ou rejeite o orçamento exibido no portal público de acompanhamento.
###### Perfis de Acesso
`Cliente` (Acesso Público)
###### Critério de Aceite / Validação
* Se aprovado: transicionar status para `EM_EXECUCAO` e disparar evento de baixa/confirmação de estoque.
* Se rejeitado: transicionar status para `CANCELADA` e acionar estorno automático de peças.

---

## 7. Métricas de Gestão Operacional

##### **RF-23** - Relatório do Tempo Médio de Execução de Serviços
###### Descrição do Domínio
O sistema deve calcular o tempo médio de execução dos serviços baseando-se no intervalo entre a data/hora do início da execução (`EM_EXECUCAO`) e a data/hora de finalização (`FINALIZADA`).
###### Perfis de Acesso
`Gerente`
###### Critério de Aceite / Validação
* Exibir relatórios com o tempo médio de atendimento agrupado por período e por mecânico responsável.
