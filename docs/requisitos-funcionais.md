# Requisitos Funcionais (RF) - Sistema de Oficina Mecânica

Este documento especifica todos os **Requisitos Funcionais (RF)** do MVP do sistema de gestão da oficina mecânica, estabelecendo as regras de negócio operacionais para as duas frentes do sistema: a **Frente da Loja** (acesso autenticado e controlado por perfis - RBAC) e a **Frente do Cliente** (acompanhamento público desautenticado e seguro).

> Documento atualizado em 28/10/2026 - Versão 1.5
---

## Matriz de Perfis e Permissões de Acesso (RBAC)

O acesso às funcionalidades da aplicação é estritamente controlado com base nos seguintes perfis:

* **`Atendente`**: Responsável pelo primeiro contato, cadastro de clientes/veículos, abertura de OS, consulta de serviços/peças e entrega final do veículo.
* **`Mecânico`**: Responsável pela avaliação técnica, diagnóstico, inclusão de itens/peças na OS, cálculo de orçamento, início e conclusão da execução da manutenção.
* **`Gerente` (Admin)**: Administrador com privilégios totais (CRUD completo em todas as entidades, gerenciamento de usuários/credenciais internas, cancelamento de OS, gestão de catálogo e relatórios de métricas).
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
O sistema deve permitir que o Gerente cadastre, consulte, atualize e desative acessos de funcionários (Atendentes e Mecânicos). Adicionalmente, na inicialização da aplicação, o sistema deve executar um script de carga inicial (*seed data*) criando o usuário administrador padrão (`admin@oficina.com`) e, opcionalmente, usuários de demonstração dos demais perfis.
###### Perfis de Acesso
`Gerente` (Acesso Exclusivo)
###### Critério de Aceite / Validação
* Apenas o perfil Gerente pode criar novas contas de funcionários e definir seus perfis (`role`).
* Armazenar senhas exclusivamente na forma de hash criptográfico (bcrypt).
* Executar a criação automatizada do usuário Gerente padrão via *seed data* no banco de dados na subida do container, com a senha lida da variável de ambiente `ADMIN_PASSWORD`. A aplicação não deve iniciar se a variável estiver ausente; nenhuma senha tem valor fixo no repositório (RNF-06).
* Quando a variável `SEED_DEMO` for `true`, criar também os usuários de demonstração `atendente@oficina.com` (Atendente) e `mecanico@oficina.com` (Mecânico), com senhas lidas das variáveis `DEMO_ATENDENTE_PASSWORD` e `DEMO_MECANICO_PASSWORD`.
* A carga inicial não deve duplicar usuários já existentes quando o container for reiniciado.

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
O sistema deve disponibilizar a listagem e consulta dos serviços ativos oferecidos pela oficina e seus respectivos valores base.
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Retornar código, nome do serviço, descrição técnica, valor base e tempo estimado de execução do serviço.
* Não listar serviços excluídos logicamente.

##### **RF-11** - Administração do Catálogo de Serviços (CRUD Amplo)
###### Descrição do Domínio
O sistema deve permitir criar novos serviços, alterar valores base e tempos estimados e excluir serviços do catálogo.
###### Perfis de Acesso
`Gerente`
###### Critério de Aceite / Validação
* Apenas o Gerente pode cadastrar, editar preços base e tempos estimados ou remover serviços do catálogo.
* Registrar o tempo estimado de execução de cada serviço, em minutos, usado na estimativa de entrega (RF-25).
* A remoção é uma exclusão lógica: o serviço deixa de ser listado e de poder ser incluído em novas OS, e as OS que já o referenciam permanecem íntegras.

##### **RF-12** - Gestão de Peças e Controle de Estoque
###### Descrição do Domínio
O sistema deve permitir a consulta, cadastro, atualização dos dados, atualização do saldo e baixa de peças e insumos. Atendentes apenas consultam peças; Mecânicos consultam peças e atualizam a quantidade em estoque; a criação de novos itens, a alteração dos dados cadastrais e a exclusão são restritas à gerência.
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente` (Listar) | `Mecânico`, `Gerente` (Atualizar quantidade em estoque) | `Gerente` (Criar, Atualizar dados cadastrais e Deletar Peças)
###### Critério de Aceite / Validação
* Controlar quantidade física, quantidade reservada, preço unitário de venda, código de referência e prazo de reposição da peça (em dias, usado na estimativa de entrega do RF-25).
* Apenas o Gerente altera preço unitário de venda, código de referência e prazo de reposição.
* O código de referência é único, inclusive entre peças excluídas, e é gravado em maiúsculas: `flt-001` e `FLT-001` são a mesma peça.
* O saldo disponível é a quantidade física menos a quantidade reservada, e nunca pode ficar negativo.
* Todo aumento de saldo aciona a alocação automática às OS com peça pendente (RF-19), na mesma transação. A quantidade física inicial informada no cadastro da peça é a exceção, pois nenhuma OS pode ter pendência de uma peça que acabou de ser cadastrada.
* A remoção é uma exclusão lógica: a peça deixa de ser listada e de poder ser incluída em novas OS, e as reservas e OS existentes permanecem íntegras.
* Uma peça com quantidade pendente em alguma OS não pode ser excluída, pois essas OS dependem da reposição dela.

---

## 5. Ciclo de Vida da Ordem de Serviço (OS)

O enunciado define seis status (`RECEBIDA`, `EM_DIAGNOSTICO`, `AGUARDANDO_APROVACAO`, `EM_EXECUCAO`, `FINALIZADA`, `ENTREGUE`). O sistema acrescenta três status para cobrir regras que a lista original não representa:

* **`AGUARDANDO_PECA`**: o cliente aprovou o orçamento, mas há peças sem saldo em estoque; a OS espera a reposição (RF-18, RF-19).
* **`AGUARDANDO_EXECUCAO`**: o orçamento foi aprovado e todas as peças estão reservadas; a OS espera o mecânico iniciar o serviço. Separar este status de `EM_EXECUCAO` faz o tempo médio de execução (RF-27) medir apenas o trabalho do mecânico.
* **`CANCELADA`**: estado final para orçamento rejeitado pelo cliente (RF-26) ou cancelamento pelo Gerente (RF-23). Sem ele, uma OS rejeitada ficaria indefinidamente em `AGUARDANDO_APROVACAO`.

##### **RF-13** - Abertura de Ordem de Serviço
###### Descrição do Domínio
O sistema deve permitir a criação de uma nova Ordem de Serviço associando cliente e veículo cadastrados. A OS é criada com o status inicial `RECEBIDA`.
###### Perfis de Acesso
`Atendente`, `Gerente`
###### Critério de Aceite / Validação
* Gerar um identificador interno (UUID) e um número da OS para uso do cliente, gravar data/hora de abertura, o usuário que abriu a OS e definir o status inicial como `RECEBIDA`.
* O número da OS é formado pelos 3 primeiros dígitos do CPF/CNPJ do cliente, um hífen e os 8 primeiros caracteres hexadecimais do UUID em maiúsculas (ex.: `123-7F3A9C2B`). Em caso de colisão com um número existente, gerar um novo UUID.

##### **RF-14** - Listagem de Ordens de Serviço
###### Descrição do Domínio
O sistema deve listar as Ordens de Serviço com filtros combináveis.
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente` (todos os perfis veem todas as OS)
###### Critério de Aceite / Validação
* Permitir filtrar por status, mecânico responsável, CPF/CNPJ do cliente ou placa do veículo e período de abertura (data inicial e data final).
* Retornar, para cada OS, número, status, nome do cliente, placa, mecânico responsável, data de abertura e valor total do orçamento, quando houver.

##### **RF-15** - Detalhamento de Ordem de Serviço
###### Descrição do Domínio
O sistema deve exibir todos os dados de uma Ordem de Serviço.
###### Perfis de Acesso
`Atendente`, `Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Retornar cliente, veículo, atendente que abriu a OS, mecânico responsável, status, serviços e peças com valores congelados, quantidades reservadas e pendentes de cada peça, valor total, datas de abertura, início da execução e finalização, estimativa de entrega (RF-25) e histórico de status (RF-24).

##### **RF-16** - Atribuição de Mecânico e Início de Diagnóstico
###### Descrição do Domínio
O sistema deve permitir que o mecânico assuma a OS, vinculando seu ID à Ordem de Serviço. No momento da vinculação, a OS muda automaticamente de `RECEBIDA` para `EM_DIAGNOSTICO`.
###### Perfis de Acesso
`Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* O status deve alterar para `EM_DIAGNOSTICO` imediatamente ao atribuir o ID do mecânico responsável.

##### **RF-17** - Inclusão de Itens e Congelamento de Valores no Orçamento
###### Descrição do Domínio
O sistema deve permitir incluir serviços e peças na OS durante a fase de diagnóstico. Ao concluir o orçamento, o sistema busca os preços vigentes dos serviços e peças, o tempo estimado de cada serviço (RF-11) e o prazo de reposição de cada peça (RF-12), e congela esses valores na OS. Assim, reajustes futuros no catálogo não alteram o valor cotado nem a estimativa de entrega (RF-25).
###### Perfis de Acesso
`Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Permitir incluir apenas serviços e peças ativos no catálogo.
* Não permitir o mesmo serviço nem a mesma peça duas vezes na OS, e exigir que a quantidade de cada peça seja um número inteiro maior que zero.
* O cálculo do orçamento é a soma exata dos valores congelados dos serviços e peças incluídos.
* Ao concluir o orçamento, a OS muda para `AGUARDANDO_APROVACAO` e a reserva de peças (RF-18) é executada na mesma transação.

##### **RF-18** - Reserva de Peças, Pendência e Estorno Automático
###### Descrição do Domínio
O sistema deve reservar as peças da OS no estoque no momento em que a OS transita para `AGUARDANDO_APROVACAO`. Quando não houver saldo suficiente, o orçamento é gerado mesmo assim, a quantidade disponível é reservada e o restante fica registrado como pendente. Caso o cliente rejeite o orçamento ou a OS seja cancelada, o sistema devolve as reservas ao estoque.
###### Perfis de Acesso
`Sistema` (Automação de Domínio / Event Dispatcher)
###### Critério de Aceite / Validação
* Para cada peça da OS, reservar a menor quantidade entre a solicitada e o saldo disponível, e registrar a diferença como quantidade pendente do item.
* Prioridade pela OS mais antiga: uma OS só pode usar saldo disponível de uma peça se nenhuma OS com data de abertura anterior tiver quantidade pendente da mesma peça. Reservas já efetuadas não são remanejadas entre OS.
* O orçamento exibido ao cliente e o detalhamento da OS informam de forma explícita quais peças estão pendentes.
* Em caso de rejeição ou cancelamento, as quantidades reservadas voltam ao saldo disponível e as pendências da OS são removidas, sem intervenção manual. Peças já baixadas no início da execução (RF-20) são consideradas consumidas e não retornam ao estoque.
* O saldo disponível nunca fica negativo.

##### **RF-19** - Liberação de OS por Reposição de Estoque
###### Descrição do Domínio
Quando o saldo de uma peça aumenta (RF-12), o sistema deve alocar automaticamente o saldo às OS com quantidade pendente dessa peça.
###### Perfis de Acesso
`Sistema` (Automação de Domínio / Event Dispatcher)
###### Critério de Aceite / Validação
* Alocar o saldo disponível às OS em `AGUARDANDO_APROVACAO` ou `AGUARDANDO_PECA` com pendência da peça, em ordem crescente de data de abertura, convertendo quantidade pendente em quantidade reservada.
* Quando uma OS em `AGUARDANDO_PECA` deixa de ter pendências, ela muda automaticamente para `AGUARDANDO_EXECUCAO`.
* A alocação, a transição de status e a atualização de saldo ocorrem na mesma transação (RNF-08).

##### **RF-20** - Início da Execução e Baixa de Peças
###### Descrição do Domínio
Com o orçamento aprovado e todas as peças reservadas, a OS fica em `AGUARDANDO_EXECUCAO` até o mecânico iniciar o serviço. No início, a OS muda para `EM_EXECUCAO`, as peças reservadas recebem baixa definitiva e o timestamp exato do início da execução é gravado.
###### Perfis de Acesso
`Mecânico` (apenas o mecânico atribuído à OS), `Gerente`
###### Critério de Aceite / Validação
* Permitir o início apenas a partir de `AGUARDANDO_EXECUCAO`.
* Recusar o início por usuário desativado, mesmo que seja o mecânico atribuído ou o Gerente.
* Dar baixa em todas as quantidades reservadas da OS (redução da quantidade física e da quantidade reservada) na mesma transação da mudança de status.
* Gravar o timestamp inicial obrigatório para o cálculo posterior do tempo médio de execução.

##### **RF-21** - Conclusão da Manutenção e Registro de Timestamp de Término
###### Descrição do Domínio
O mecânico deve sinalizar a conclusão técnica da manutenção, alterando o status da OS de `EM_EXECUCAO` para `FINALIZADA` e gravando o timestamp final.
###### Perfis de Acesso
`Mecânico`, `Gerente`
###### Critério de Aceite / Validação
* Gravar o timestamp final e impedir novas alterações de itens na OS.

##### **RF-22** - Entrega do Veículo ao Cliente
###### Descrição do Domínio
Após a conclusão técnica e acerto comercial, o atendente altera o status da OS de `FINALIZADA` para `ENTREGUE`. Esta transição é de responsabilidade exclusiva da equipe de atendimento.
###### Perfis de Acesso
`Atendente`, `Gerente`
###### Critério de Aceite / Validação
* Apenas Atendentes e Gerentes podem realizar a mudança de status para `ENTREGUE`. Mecânicos não possuem permissão para esta transição.

##### **RF-23** - Cancelamento de OS pelo Gerente
###### Descrição do Domínio
O sistema deve permitir que o Gerente cancele uma OS em situações excepcionais de loja. O cancelamento é a única alteração de status fora do fluxo normal; não há alteração arbitrária de status.
###### Perfis de Acesso
`Gerente` (Acesso Exclusivo)
###### Critério de Aceite / Validação
* Permitir o cancelamento a partir de `RECEBIDA`, `EM_DIAGNOSTICO`, `AGUARDANDO_APROVACAO`, `AGUARDANDO_PECA`, `AGUARDANDO_EXECUCAO` e `EM_EXECUCAO`. OS em `FINALIZADA`, `ENTREGUE` ou `CANCELADA` não podem ser canceladas.
* Exigir o motivo do cancelamento e registrá-lo no histórico de status da OS (RF-24).
* Estornar as reservas conforme o RF-18.

##### **RF-24** - Histórico de Status da OS
###### Descrição do Domínio
O sistema deve registrar cada transição de status da OS em um histórico imutável, usado para auditoria, para o detalhamento da OS e para as métricas do RF-27.
###### Perfis de Acesso
`Sistema` (registro) | `Atendente`, `Mecânico`, `Gerente` (consulta via RF-15)
###### Critério de Aceite / Validação
* Cada registro contém status anterior, novo status, data/hora, origem da ação (`USUARIO`, `CLIENTE` ou `SISTEMA`), identificador do usuário quando a origem for `USUARIO` e motivo.
* O motivo é obrigatório no cancelamento pelo Gerente (RF-23).
* A abertura da OS gera o primeiro registro, sem status anterior.
* Registros do histórico não podem ser alterados nem removidos.

---

## 6. Acompanhamento Público e Segurança do Cliente (Frente do Cliente)

##### **RF-25** - Consulta Pública de Status da OS
###### Descrição do Domínio
O sistema deve disponibilizar um endpoint público (sem exigência de JWT) permitindo que o cliente consulte o status em tempo real da sua OS fornecendo obrigatoriamente a combinação do **Número da OS + CPF/CNPJ** do titular.
###### Perfis de Acesso
`Cliente` (Acesso Público Desautenticado)
###### Critério de Aceite / Validação
* Retornar o status atual, descrição resumida dos serviços, peças pendentes, valor total do orçamento e estimativa de entrega.
* Ocultar dados pessoais sensíveis do cliente e custos internos de fornecedores.
* Retornar a mesma resposta de "não encontrada" quando o número não existir ou o CPF/CNPJ não corresponder, sem indicar qual dos dois está errado.
* Calcular a estimativa de entrega como uma data, em tempo corrido, a partir da duração dos serviços (soma dos tempos estimados congelados na OS, RF-17) e do prazo de peças (maior prazo de reposição congelado na OS entre as peças pendentes, RF-17):

| Status da OS | Estimativa de entrega |
| :--- | :--- |
| `RECEBIDA`, `EM_DIAGNOSTICO` | Não exibida, pois os serviços ainda não foram definidos |
| `AGUARDANDO_APROVACAO`, `AGUARDANDO_PECA` | Momento da consulta + prazo de peças + duração dos serviços |
| `AGUARDANDO_EXECUCAO` | Momento da consulta + duração dos serviços |
| `EM_EXECUCAO` | Início da execução + duração dos serviços |
| `FINALIZADA`, `ENTREGUE` | Data de finalização registrada |
| `CANCELADA` | Não exibida |

##### **RF-26** - Aprovação ou Rejeição de Orçamento pelo Cliente
###### Descrição do Domínio
O sistema deve permitir que o cliente aprove ou rejeite o orçamento exibido no portal público de acompanhamento, identificando-se da mesma forma que no RF-25.
###### Perfis de Acesso
`Cliente` (Acesso Público)
###### Critério de Aceite / Validação
* Permitir a aprovação ou a rejeição apenas quando a OS estiver em `AGUARDANDO_APROVACAO`.
* Se aprovado sem peças pendentes: transicionar o status para `AGUARDANDO_EXECUCAO`.
* Se aprovado com peças pendentes: transicionar o status para `AGUARDANDO_PECA`; a OS segue para `AGUARDANDO_EXECUCAO` quando as peças forem repostas (RF-19).
* Se rejeitado: transicionar o status para `CANCELADA` e acionar o estorno automático das reservas (RF-18).

---

## 7. Métricas de Gestão Operacional

##### **RF-27** - Relatório de Tempos Médios da OS
###### Descrição do Domínio
O sistema deve calcular indicadores de tempo das Ordens de Serviço a partir dos timestamps da OS e do histórico de status (RF-24).
###### Perfis de Acesso
`Gerente`
###### Critério de Aceite / Validação
* **Tempo médio de execução:** intervalo entre o início da execução (`EM_EXECUCAO`) e a finalização (`FINALIZADA`), agrupado por período e por mecânico responsável.
* **Tempo médio de espera por peça:** intervalo entre a entrada e a saída de `AGUARDANDO_PECA`, agrupado por período.
* **Tempo médio total da OS:** intervalo entre a abertura e a finalização (`FINALIZADA`), incluindo todas as esperas, agrupado por período.
