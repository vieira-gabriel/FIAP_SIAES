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

Fluxo público do cliente, sem login (RF-25).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Cliente | Entra com credenciais | Verifica número da OS e credencial do cliente | Acessa página de acompanhamento | RF-25 |
| — | — | Busca status e infos da OS | Exibe status e info da OS | RF-25 |

### 2. Criação de Ordem de Serviço

Todos os eventos desta área pertencem ao agregado `OrdemServico`. Cada linha segue a ordem do fluxo no board.

| Ator | Comando | Evento | Políticas disparadas pelo evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Atendente | Abrir OS | OS aberta | — | RF-13 |
| Atendente | Cadastrar / Identificar cliente | Cliente vinculado à OS | — | RF-04 |
| Atendente | Vincular veículo | Veículo vinculado à OS | Gera número da OS; Status OS "Recebida" (`RECEBIDA`) | RF-07, RF-13 |
| Mecânico | Inicia diagnóstico | Vincula mecânico à OS | Status OS "Em diagnóstico" (`EM_DIAGNOSTICO`) | RF-16 |
| Mecânico | Adiciona serviços à OS | Serviços vinculados | — | RF-17 |
| Mecânico | Adiciona peças à OS | Peças vinculadas | Sinaliza se houver peça pendente; Reservar peças | RF-17, RF-18 |
| — (política "Gera orçamento") | — | Orçamento gerado | Status OS "Aguardando aprovação" (`AGUARDANDO_APROVACAO`); Envio para email do cliente | RF-17 |
| Cliente (modelo de leitura "Orçamento de serviço") | Aprovar / reprovar OS | OS aprovada | Confere se há peça pendente → Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`) ou Status OS "Aguardando peça" (`AGUARDANDO_PECA`) | RF-26 |
| Cliente (modelo de leitura "Orçamento de serviço") | Aprovar / reprovar OS | OS reprovada | Status OS "Cancelada" (`CANCELADA`) | RF-18, RF-26 |

O evento "Saldo da peça atualizado", da área Gestão administrativa (seção 3.3), dispara a política "Confere se há OS com pendência da peça atualizada", que leva a OS de "Aguardando peça" para "Aguardando execução" (RF-19).

### 3. Gestão Administrativa

#### 3.1. Acesso

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente, Mecânico | Entra com credenciais | Autenticar credenciais | Exibir opções do menu | RF-01 |

#### 3.2. Serviços

Comando de entrada: Seleciona opção "Serviços" → evento "Lista Serviços" (RF-10).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente | Adicionar serviço | Validar se é Gerente | Serviço adicionado | RF-11 |
| Gerente | Atualizar serviço | Validar se é Gerente | Serviço atualizado | RF-11 |
| Gerente | Remover serviço | Validar se é Gerente | Serviço removido | RF-11 |
| Gerente, Atendente, Mecânico | Procurar serviço | — | Exibe resultado da busca | RF-10 |

#### 3.3. Peças

Comando de entrada: Seleciona opção "Peças" → evento "Lista Peças" (RF-12).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente | Adicionar peça | Validar se é Gerente | Peça cadastrada | RF-12 |
| Gerente | Atualizar dados da peça | Validar se é Gerente | Dados da peça atualizados | RF-12 |
| Gerente, Mecânico | Atualizar saldo da peça | Validar se é Gerente ou Mecânico | Saldo da peça atualizado | RF-12, RF-19 |
| — | — | Confere se há OS com pendência da peça atualizada | Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`) | RF-19 |
| Gerente | Remover peça | Validar se é Gerente | Peça removida (exclusão lógica) | RF-12 |
| Gerente, Atendente, Mecânico | Procurar peça | — | Exibe resultado da busca | RF-12 |

#### 3.4. Clientes

Comando de entrada: Seleciona opção "Clientes" → evento "Lista Clientes".

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente | Adicionar cliente | Validar se é Gerente ou Atendente | Cliente adicionado | RF-04, RF-05 |
| Gerente, Atendente | Atualizar cliente | Validar se é Gerente ou Atendente | Cliente atualizado | RF-04, RF-05 |
| Gerente | Remover cliente | Validar se é Gerente | Cliente removido | RF-06 |
| Gerente, Atendente, Mecânico | Procurar cliente | — | Exibe resultado da busca | RF-04 |

#### 3.5. Veículos

Comando de entrada: Seleciona opção "Veículos" → evento "Lista Veículos".

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente | Adicionar veículo | Validar se é Gerente ou Atendente | Veículo adicionado | RF-07, RF-08 |
| Gerente, Atendente | Atualizar veículo | Validar se é Gerente ou Atendente | Veículo atualizado | RF-07, RF-08 |
| Gerente, Atendente | Remover veículo | Validar se é Gerente ou Atendente | Veículo removido | RF-09 |
| Gerente, Atendente, Mecânico | Procurar veículo | — | Exibe resultado da busca | RF-07 |

#### 3.6. Ordens de Serviço

Comando de entrada: Seleciona opção "OSs" → evento "Lista OSs" (RF-14).

| Ator | Comando | Política | Evento | Requisito |
| :--- | :--- | :--- | :--- | :--- |
| Gerente, Atendente | Atualizar dados da OS | Validar se é Gerente ou Atendente | Dados da OS atualizados | RF-13 |
| Gerente, Atendente | Criar OS | Validar se é Gerente ou Atendente | Inicia o fluxo da seção 2 | RF-13 |
| Gerente, Atendente, Mecânico | Atualizar status da OS | — | Status da OS atualizado | RF-16 a RF-22 |
| Gerente | Cancelar OS | Validar se é Gerente | OS cancelada | RF-23 |
| Gerente, Atendente, Mecânico | Procurar OS | — | Exibe resultado da busca | RF-14, RF-15 |

O cancelamento pelo Gerente substitui o comando "Remover OS" das versões anteriores do board: não há remoção de OS.

### 4. Divergências Conhecidas

| Ponto | Board | Requisitos | Tratamento |
| :--- | :--- | :--- | :--- |
| Alocação de peças repostas | Uma única política, "Confere se há OS com pendência da peça atualizada" | RF-19 detalha a alocação do saldo às OS com peça pendente, da OS mais antiga para a mais nova, e a liberação apenas das OS sem nenhuma pendência | O board registra só a reação ao evento; o algoritmo do RF-19 será detalhado em diagrama próprio em `docs/ddd/diagramas.pdf` |
| "Atualizar status da OS" | Comando sem política de permissão | RF-16 a RF-22 definem quem faz cada transição; não há alteração arbitrária de status (RF-23) | A máquina de estados da Linguagem Ubíqua (§5) prevalece |
