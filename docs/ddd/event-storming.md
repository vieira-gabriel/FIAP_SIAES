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

O board marca apenas o agregado `OrdemServico` nesta área. A política "Reservar peças" altera também o agregado `EstoquePeca` da Linguagem Ubíqua, que o board não representa. Cada linha segue a ordem do fluxo no board.

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
| Gerente, Atendente | Atualizar dados da OS | Validar se é Gerente ou Atendente | Dados da OS atualizados | Sem RF (seção 5) |
| Gerente, Atendente | Criar OS | Validar se é Gerente ou Atendente | Inicia o fluxo da seção 2 | RF-13 |
| Gerente, Atendente, Mecânico | Atualizar status da OS | — | Status da OS atualizado | RF-16 a RF-22 |
| Gerente | Cancelar OS | Validar se é Gerente | OS cancelada | RF-23 |
| Gerente, Atendente, Mecânico | Procurar OS | — | Exibe resultado da busca | RF-14, RF-15 |

O cancelamento pelo Gerente substitui o comando "Remover OS" das versões anteriores do board: não há remoção de OS.

### 4. Correspondência com a Linguagem Ubíqua

Os nomes do board diferem dos termos da Linguagem Ubíqua em alguns pontos. No código, use sempre a coluna da direita.

| Nome no board | Termo da Linguagem Ubíqua | Referência |
| :--- | :--- | :--- |
| Abrir OS / OS aberta | Abrir OS | Linguagem Ubíqua §5, RF-13 |
| Inicia diagnóstico / Vincula mecânico à OS | `atribuir_mecanico` | Linguagem Ubíqua §5, RF-16 |
| Gera orçamento / Orçamento gerado | `finalizar_orcamento` | Linguagem Ubíqua §5, RF-17 |
| Reservar peças | Reserva | Linguagem Ubíqua §1, RF-18 |
| Sinaliza se houver peça pendente | Peça Pendente | Linguagem Ubíqua §1, RF-18 |
| Aprovar / reprovar OS → OS aprovada | `aprovar_orcamento` | Linguagem Ubíqua §5, RF-26 |
| Aprovar / reprovar OS → OS reprovada | `rejeitar_orcamento` | Linguagem Ubíqua §5, RF-26 |
| Confere se há OS com pendência da peça atualizada | `liberar_para_execucao` | Linguagem Ubíqua §5, RF-19 |
| Cancelar OS / OS cancelada | `cancelar(motivo)` | Linguagem Ubíqua §5, RF-23 |
| Remover serviço, peça, cliente ou veículo | Exclusão lógica | RF-06, RF-09, RF-11, RF-12 |
| Peça | Peça / Insumo | Linguagem Ubíqua §1 |
| Atualizar saldo da peça | Atualização de saldo de `EstoquePeca` | Linguagem Ubíqua §1, RF-12 |

### 5. Divergências Conhecidas

| Ponto | Board | Requisitos | Tratamento |
| :--- | :--- | :--- | :--- |
| Momento da reserva de peças | A política "Reservar peças" é disparada por "Peças vinculadas", antes de "Gera orçamento" | RF-17 e RF-18 reservam as peças na conclusão do orçamento, na mesma transação da passagem para `AGUARDANDO_APROVACAO` | Os requisitos prevalecem |
| Envio de e-mail ao cliente | A política "Envio para email do cliente" é disparada por "Orçamento gerado" | Nenhum RF ou RNF define envio de e-mail | Fora do MVP até o grupo decidir incluí-lo nos requisitos |
| Estorno de reservas | "OS reprovada" e "OS cancelada" não disparam política de estorno | RF-18, RF-23 e RF-26 exigem o estorno automático das reservas | Os requisitos prevalecem |
| Exclusão lógica | Os eventos "removido" não indicam o tipo de exclusão | RF-06, RF-09, RF-11 e RF-12 definem exclusão lógica | Os requisitos prevalecem |
| Etapas sem evento próprio | Início da execução, conclusão, entrega e histórico de status ficam no comando genérico "Atualizar status da OS"; relatório e gestão de usuários não aparecem | RF-20 (com baixa das peças), RF-21, RF-22, RF-24, RF-27 e RF-03 | Os requisitos e a máquina de estados da Linguagem Ubíqua (§5) prevalecem |
| "Atualizar dados da OS" | Permitido a Gerente e Atendente | Nenhum RF define a atualização dos dados da OS; a Linguagem Ubíqua (§3) dá também ao Mecânico a permissão de atualizar OS | Pendente de decisão do grupo |
| Identificação do cliente | O comando "Entra com credenciais" sugere login | RF-25 e RF-26 dispensam login e exigem número da OS com CPF/CNPJ | Os requisitos prevalecem |
| Gerente na abertura e no diagnóstico | "Abrir OS" tem só o Atendente e "Inicia diagnóstico" tem só o Mecânico | RF-13 e RF-16 incluem o Gerente | Os requisitos prevalecem |
| Agregado de estoque | Só o agregado `OrdemServico` aparece no board | A Linguagem Ubíqua (§1) define o agregado `EstoquePeca` | A Linguagem Ubíqua prevalece |
| Alocação de peças repostas | Uma única política, "Confere se há OS com pendência da peça atualizada" | RF-19 detalha a alocação do saldo às OS com peça pendente, da OS mais antiga para a mais nova, e a liberação apenas das OS sem nenhuma pendência | O board registra só a reação ao evento; o algoritmo do RF-19 será detalhado em diagrama próprio em `docs/ddd/diagramas.pdf` |
| "Atualizar status da OS" | Comando sem política de permissão | RF-16 a RF-22 definem quem faz cada transição; não há alteração arbitrária de status (RF-23) | A máquina de estados da Linguagem Ubíqua (§5) prevalece |
