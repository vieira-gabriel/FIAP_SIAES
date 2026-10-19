# Event Storming

Este documento registra onde encontrar o Event Storming do sistema de gestão da oficina mecânica.

| Artefato | Local |
| :--- | :--- |
| Board no Miro (acesso público para leitura) | [Abrir o board](https://miro.com/app/board/uXjVEebLYnw=/?share_link_id=963442578083) |
| Exportação em PDF | [event-storming.pdf](event-storming.pdf) |

O board é a fonte da verdade do Event Storming. Sempre que o board for alterado, reexporte o PDF no mesmo PR.

## Transcrição do Board

A transcrição abaixo reproduz os post-its do board com os nomes usados nele, com a concordância de gênero e número corrigida (ex.: "Peça removido" no board aparece como "Peça removida"). A coluna "Requisito" liga cada passo aos requisitos funcionais e aos valores de `StatusOS` da Linguagem Ubíqua.

Legenda dos post-its:

| Cor no board | Elemento |
| :--- | :--- |
| Amarelo-claro | Ator |
| Azul | Comando |
| Roxo | Política (regra ou reação automática) |
| Amarelo | Evento de domínio |
| Verde | Modelo de leitura |
| Marrom | Agregado |

### 1. Acompanhar OS

Fluxo público do cliente, sem login (RF-25, RF-26).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Cliente | Entra com credenciais | Verifica número da OS e credencial do cliente | Acessa página de acompanhamento | RF-25 |
| — | — | Busca status e infos da OS | Exibe status e info da OS | RF-25 |
| — (modelo de leitura "Orçamento da OS") | — | Orçamento pendente de aprovação | Exibe orçamento | RF-25, RF-26 |
| Cliente | Orçamento aprovado | — | OS aprovada | RF-26 |
| Cliente | Orçamento reprovado | — | OS reprovada | RF-26 |

### 2. Criação de Ordem de Serviço

O board marca apenas o agregado `OrdemServico` nesta área. A política "Reservar peças" altera também o agregado `EstoquePeca` da Linguagem Ubíqua, que o board não representa. Cada linha segue a ordem do fluxo no board.

| Ator | Comando | Evento | Políticas disparadas pelo evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Atendente | Abrir OS | OS aberta | — | RF-13 |
| Atendente | Cadastrar / Identificar cliente | Cliente vinculado à OS | — | RF-04 |
| Atendente | Vincular veículo | Veículo vinculado à OS | Gera número da OS; Status OS "Recebida" (`RECEBIDA`) | RF-07, RF-13 |
| Mecânico | Inicia diagnóstico | Vincula mecânico à OS | Status OS "Em diagnóstico" (`EM_DIAGNOSTICO`) | RF-16 |
| Mecânico | Adiciona serviços à OS | Serviços vinculados | — | RF-17 |
| Mecânico | Adiciona peças à OS | Peças vinculadas | Sinaliza se houver peça pendente | RF-17, RF-18 |
| — (política "Gera orçamento") | — | Orçamento gerado | Reservar peças; Status OS "Aguardando aprovação" (`AGUARDANDO_APROVACAO`); Disponibiliza o orçamento no acompanhamento da OS | RF-17, RF-18, RF-25 |
| Cliente | Aprova / reprova OS | OS aprovada | Confere se há peça pendente → Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`) ou Status OS "Aguardando peça" (`AGUARDANDO_PECA`) | RF-26 |
| Cliente | Aprova / reprova OS | OS reprovada | Estorno de peças; Status OS "Cancelada" (`CANCELADA`) | RF-18, RF-26 |

A continuação do fluxo depois de "OS aprovada", incluindo a liberação da OS em "Aguardando peça" pela reposição do estoque, está na área "Ciclo de vida da OS aprovada" (seção 3).

### 3. Ciclo de Vida da OS Aprovada

Ciclo de vida da OS desde a aprovação do orçamento até a finalização (RF-19 a RF-21, RF-23, RF-24). A área começa no evento "OS aprovada", o mesmo das áreas "Acompanhar OS" e "Criação de ordem de serviço", e marca os dois agregados alterados: `OrdemServico` e `EstoquePeca`. Os eventos "Saldo da peça atualizado" e "OS cancelada" são os mesmos das áreas "Peças" e "Ordens de Serviço" (seções 4.3 e 4.6). Cada linha segue a ordem do fluxo no board.

| Ator | Comando | Política | Agregado | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- | :--- |
| — | — | — | `OrdemServico` | OS aprovada | RF-26 |
| — | — | Confere se há peça pendente | `OrdemServico` | Status OS "Aguardando peça" (`AGUARDANDO_PECA`) ou Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`) | RF-26 |
| Gerente, Mecânico | Atualizar saldo da peça | Validar se é Gerente ou Mecânico | `EstoquePeca` | Saldo da peça atualizado | RF-12 |
| — (modelo de leitura "OS com pendência da peça por data de abertura") | — | Aloca o saldo às OS com pendência da peça, da OS mais antiga para a mais nova (Aguardando aprovação ou Aguardando peça) | `EstoquePeca` | Pendência convertida em reserva | RF-18, RF-19 |
| — | — | Confere se a OS em "Aguardando peça" ainda tem pendências | `OrdemServico` | Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`), apenas quando não resta pendência; caso contrário, a OS continua em "Aguardando peça" | RF-19 |
| Mecânico atribuído, Gerente | Iniciar execução | Validar se é o mecânico atribuído ou Gerente | `OrdemServico` | Execução iniciada: Status OS "Em execução" (`EM_EXECUCAO`), com gravação da data de início | RF-20 |
| — | — | Dar baixa nas peças reservadas | `EstoquePeca` | Peças baixadas | RF-20 |
| Mecânico, Gerente | Concluir manutenção | Validar se é Mecânico ou Gerente | `OrdemServico` | Manutenção concluída: Status OS "Finalizada" (`FINALIZADA`), com gravação da data de finalização e bloqueio dos itens | RF-21 |
| — | — | Registra a transição no histórico | `OrdemServico` | Transição registrada no histórico | RF-24 |
| Gerente | Cancelar OS (com motivo) | Validar se é Gerente | `OrdemServico` | OS cancelada | RF-23 |
| — | — | Estorna as reservas; peças já baixadas não voltam ao estoque | `EstoquePeca` | Reservas estornadas | RF-18 |

Ligações entre os post-its:

* "OS aprovada" dispara "Confere se há peça pendente", que leva a "Aguardando peça" ou a "Aguardando execução".
* No ramo "Aguardando peça", a OS espera o comando "Atualizar saldo da peça". O evento "Saldo da peça atualizado" dispara a alocação, que lê o modelo de leitura das OS pendentes; cada "Pendência convertida em reserva" dispara a conferência das pendências restantes, que libera a OS para "Aguardando execução" (RF-19).
* A partir de "Aguardando execução", o comando "Iniciar execução" gera "Execução iniciada", que dispara a baixa das peças reservadas na mesma transação (RF-20). O comando "Concluir manutenção" gera "Manutenção concluída", fim da área.
* Todo evento de mudança de status ("Aguardando peça", "Aguardando execução", "Execução iniciada", "Manutenção concluída" e "OS cancelada") dispara "Registra a transição no histórico" (RF-24).
* O comando "Cancelar OS" pode partir de "Aguardando peça", "Aguardando execução" ou "Execução iniciada" (RF-23); "OS cancelada" dispara o estorno das reservas (RF-18).

### 4. Gestão Administrativa

#### 4.1. Acesso

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente, Mecânico | Entra com credenciais | Autenticar credenciais | Exibir opções do menu | RF-01 |

#### 4.2. Serviços

Comando de entrada: Seleciona opção "Serviços" → evento "Lista Serviços" (RF-10).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente | Adicionar serviço | Validar se é Gerente | Serviço adicionado | RF-11 |
| Gerente | Atualizar serviço | Validar se é Gerente | Serviço atualizado | RF-11 |
| Gerente | Remover serviço | Validar se é Gerente | Serviço removido | RF-11 |
| Gerente, Atendente, Mecânico | Procurar serviço | — | Exibe resultado da busca | RF-10 |

#### 4.3. Peças

Comando de entrada: Seleciona opção "Peças" → evento "Lista Peças" (RF-12).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente | Adicionar peça | Validar se é Gerente | Peça cadastrada | RF-12 |
| Gerente | Atualizar dados da peça | Validar se é Gerente | Dados da peça atualizados | RF-12 |
| Gerente, Mecânico | Atualizar saldo da peça | Validar se é Gerente ou Mecânico | Saldo da peça atualizado | RF-12, RF-19 |
| — | — | Confere se há OS com pendência da peça atualizada | Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`) | RF-19 |
| Gerente | Remover peça | Validar se é Gerente | Peça removida (exclusão lógica) | RF-12 |
| Gerente, Atendente, Mecânico | Procurar peça | — | Exibe resultado da busca | RF-12 |

#### 4.4. Clientes

Comando de entrada: Seleciona opção "Clientes" → evento "Lista Clientes".

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente | Adicionar cliente | Validar se é Gerente ou Atendente | Cliente adicionado | RF-04, RF-05 |
| Gerente, Atendente | Atualizar cliente | Validar se é Gerente ou Atendente | Cliente atualizado | RF-04, RF-05 |
| Gerente | Remover cliente | Validar se é Gerente | Cliente removido | RF-06 |
| Gerente, Atendente, Mecânico | Procurar cliente | — | Exibe resultado da busca | RF-04 |

#### 4.5. Veículos

Comando de entrada: Seleciona opção "Veículos" → evento "Lista Veículos".

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente | Adicionar veículo | Validar se é Gerente ou Atendente | Veículo adicionado | RF-07, RF-08 |
| Gerente, Atendente | Atualizar veículo | Validar se é Gerente ou Atendente | Veículo atualizado | RF-07, RF-08 |
| Gerente, Atendente | Remover veículo | Validar se é Gerente ou Atendente | Veículo removido | RF-09 |
| Gerente, Atendente, Mecânico | Procurar veículo | — | Exibe resultado da busca | RF-07 |

#### 4.6. Ordens de Serviço

Comando de entrada: Seleciona opção "OSs" → evento "Lista OSs" (RF-14).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente | Atualizar dados da OS | Validar se é Gerente ou Atendente | Dados da OS atualizados | Sem RF (seção 6) |
| Gerente, Atendente | Criar OS | Validar se é Gerente ou Atendente | Inicia o fluxo da seção 2 | RF-13 |
| Gerente, Atendente, Mecânico | Atualizar status da OS | — | Status da OS atualizado | RF-16 a RF-22 |
| Gerente | Cancelar OS | Validar se é Gerente | OS cancelada | RF-23 |
| Gerente, Atendente, Mecânico | Procurar OS | — | Exibe resultado da busca | RF-14, RF-15 |

O evento "OS cancelada" dispara a política de estorno das reservas (RF-18, RF-23), detalhada na área "Ciclo de vida da OS aprovada" (seção 3).

O cancelamento pelo Gerente substitui o comando "Remover OS" das versões anteriores do board: não há remoção de OS.

### 5. Correspondência com a Linguagem Ubíqua

Os nomes do board diferem dos termos da Linguagem Ubíqua em alguns pontos. No código, use sempre a coluna da direita.

| Nome no board | Termo da Linguagem Ubíqua | Referência |
| :--- | :--- | :--- |
| Abrir OS / OS aberta | Abrir OS | Linguagem Ubíqua §5, RF-13 |
| Inicia diagnóstico / Vincula mecânico à OS | `atribuir_mecanico` | Linguagem Ubíqua §5, RF-16 |
| Gera orçamento / Orçamento gerado | `finalizar_orcamento` | Linguagem Ubíqua §5, RF-17 |
| Reservar peças | Reserva | Linguagem Ubíqua §1, RF-18 |
| Sinaliza se houver peça pendente | Peça Pendente | Linguagem Ubíqua §1, RF-18 |
| Orçamento aprovado; Aprova / reprova OS → OS aprovada | `aprovar_orcamento` | Linguagem Ubíqua §5, RF-26 |
| Orçamento reprovado; Aprova / reprova OS → OS reprovada | `rejeitar_orcamento` | Linguagem Ubíqua §5, RF-26 |
| Estorno de peças | Estorno (das quantidades reservadas) | Linguagem Ubíqua §1, RF-18 |
| Confere se há OS com pendência da peça atualizada | `liberar_para_execucao` | Linguagem Ubíqua §5, RF-19 |
| Aloca o saldo às OS com pendência da peça / Pendência convertida em reserva | Peça Pendente (alocação na reposição do estoque) | Linguagem Ubíqua §1, RF-19 |
| Confere se a OS em "Aguardando peça" ainda tem pendências | `liberar_para_execucao` | Linguagem Ubíqua §5, RF-19 |
| Iniciar execução / Execução iniciada | `iniciar_execucao` | Linguagem Ubíqua §5, RF-20 |
| Dar baixa nas peças reservadas / Peças baixadas | Baixa | Linguagem Ubíqua §1, RF-20 |
| Concluir manutenção / Manutenção concluída | `concluir_manutencao` | Linguagem Ubíqua §5, RF-21 |
| Registra a transição no histórico | Histórico de Status | RF-24 |
| Estorna as reservas / Reservas estornadas | Estorno (das quantidades reservadas) | Linguagem Ubíqua §1, RF-18 |
| Cancelar OS / OS cancelada | `cancelar(motivo)` | Linguagem Ubíqua §5, RF-23 |
| Remover serviço, peça, cliente ou veículo | Exclusão lógica | RF-06, RF-09, RF-11, RF-12 |
| Peça | Peça / Insumo | Linguagem Ubíqua §1 |
| Atualizar saldo da peça | Atualização de saldo de `EstoquePeca` | Linguagem Ubíqua §1, RF-12 |

### 6. Divergências Conhecidas

| Ponto | Board | Requisitos | Tratamento |
| :--- | :--- | :--- | :--- |
| Exclusão lógica | Os eventos "removido" não indicam o tipo de exclusão | RF-06, RF-09, RF-11 e RF-12 definem exclusão lógica | Decisão do grupo: o tipo de exclusão fica registrado só nos requisitos, e o board permanece como está |
| Etapas sem evento próprio | A entrega do veículo fica no comando genérico "Atualizar status da OS"; relatório e gestão de usuários não aparecem. Início da execução, conclusão e histórico de status estão na área "Ciclo de vida da OS aprovada" (seção 3) | RF-22, RF-27 e RF-03 | Os requisitos e a máquina de estados da Linguagem Ubíqua (§5) prevalecem |
| "Atualizar dados da OS" | Permitido a Gerente e Atendente | Nenhum RF define a atualização dos dados da OS; a Linguagem Ubíqua (§3) dá também ao Mecânico a permissão de atualizar OS | Pendente de decisão do grupo |
| Identificação do cliente | O comando "Entra com credenciais" sugere login | RF-25 e RF-26 dispensam login e exigem número da OS com CPF/CNPJ | Os requisitos prevalecem |
| Gerente na abertura e no diagnóstico | "Abrir OS" tem só o Atendente e "Inicia diagnóstico" tem só o Mecânico | RF-13 e RF-16 incluem o Gerente | Os requisitos prevalecem |
| Agregado de estoque | O agregado `EstoquePeca` aparece só na área "Ciclo de vida da OS aprovada"; nas áreas "Criação de ordem de serviço" e "Peças", a reserva e a atualização de saldo não indicam o agregado | A Linguagem Ubíqua (§1) define o agregado `EstoquePeca` | A Linguagem Ubíqua prevalece |
| "Atualizar status da OS" | Comando sem política de permissão | RF-16 a RF-22 definem quem faz cada transição; não há alteração arbitrária de status (RF-23) | A máquina de estados da Linguagem Ubíqua (§5) prevalece |
