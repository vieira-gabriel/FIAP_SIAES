# Event Storming

Este documento registra onde encontrar o Event Storming do sistema de gestão da oficina mecânica, a transcrição do board e o catálogo dos eventos de domínio (seção 7).

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

Ciclo de vida da OS desde a aprovação do orçamento até a finalização ou o cancelamento (RF-19 a RF-21, RF-23). O board marca os dois agregados da área: "Ordem de Serviço" (`OrdemServico`) e "Estoque de peças" (`EstoquePeca`). O comando "Aprova / reprova OS" e os comandos "Atualizar saldo da peça" e "Cancelar OS" são os mesmos das áreas "Criação de ordem de serviço", "Peças" e "Ordens de Serviço" (seções 2, 4.3 e 4.6). Cada linha segue a ordem do fluxo no board; como na seção 2, as mudanças de status aparecem como políticas.

| Ator | Comando | Agregado | Evento | Políticas disparadas pelo evento | Requisito |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Cliente | Aprova / reprova OS | `OrdemServico` | OS aprovada | Confere se há peça pendente → Status OS "Aguardando peça" (`AGUARDANDO_PECA`) ou Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`) | RF-26 |
| Mecânico, Gerente | Atualizar saldo da peça | `EstoquePeca` | Saldo da peça atualizado | Conferir se há OS com pendência da peça atualizada (lê o modelo de leitura "OS com pendência da peça por data de abertura") → Aloca peça pendente nas OS mais antigas → Status OS "Aguardando execução" (`AGUARDANDO_EXECUCAO`) | RF-12, RF-18, RF-19 |
| Mecânico, Gerente | Inicia execução | `OrdemServico` | Serviço iniciado | Atribui mecânico à OS → evento "Mecânico atribuído"; Status OS "Em execução" (`EM_EXECUCAO`); Grava data e hora de início; Dar baixa nas peças | RF-20 |
| — (política "Dar baixa nas peças") | — | `EstoquePeca` | Baixa de peças utilizadas | — | RF-20 |
| Mecânico, Gerente | Concluir manutenção | `OrdemServico` | OS concluída | Status OS "Finalizada" (`FINALIZADA`) | RF-21 |
| Gerente | Cancelar OS | `OrdemServico` | OS cancelada | Status OS "Cancelada" (`CANCELADA`) | RF-23 |
| — (política Status OS "Cancelada") | — | `EstoquePeca` | Estorno de peças | — | RF-18, RF-23 |

Ligações entre os post-its:

* A política Status OS "Aguardando peça" e a política "Conferir se há OS com pendência da peça atualizada" estão ligadas: a OS em "Aguardando peça" espera o evento "Saldo da peça atualizado".
* A política Status OS "Aguardando execução" leva ao comando "Inicia execução".
* O evento "Serviço iniciado" leva ao comando "Concluir manutenção".
* O board não indica a condição de liberação do RF-19: a OS só passa para "Aguardando execução" quando não lhe resta nenhuma peça pendente.
* O board não indica de quais status parte o cancelamento; o RF-23 permite cancelar de `RECEBIDA` até `EM_EXECUCAO`. As peças já baixadas no início da execução não voltam ao estoque (RF-18).

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
| Aloca peça pendente nas OS mais antigas | Peça Pendente (alocação na reposição do estoque) | Linguagem Ubíqua §1, RF-19 |
| Inicia execução / Serviço iniciado | `iniciar_execucao` | Linguagem Ubíqua §5, RF-20 |
| Dar baixa nas peças / Baixa de peças utilizadas | Baixa | Linguagem Ubíqua §1, RF-20 |
| Concluir manutenção / OS concluída | `concluir_manutencao` | Linguagem Ubíqua §5, RF-21 |
| Estorno de peças (após "OS cancelada") | Estorno (das quantidades reservadas) | Linguagem Ubíqua §1, RF-18 |
| Cancelar OS / OS cancelada | `cancelar(motivo)` | Linguagem Ubíqua §5, RF-23 |
| Remover serviço, peça, cliente ou veículo | Exclusão lógica | RF-06, RF-09, RF-11, RF-12 |
| Peça | Peça / Insumo | Linguagem Ubíqua §1 |
| Atualizar saldo da peça | Atualização de saldo de `EstoquePeca` | Linguagem Ubíqua §1, RF-12 |

### 6. Divergências Conhecidas

| Ponto | Board | Requisitos | Tratamento |
| :--- | :--- | :--- | :--- |
| Exclusão lógica | Os eventos "removido" não indicam o tipo de exclusão | RF-06, RF-09, RF-11 e RF-12 definem exclusão lógica | Decisão do grupo: o tipo de exclusão fica registrado só nos requisitos, e o board permanece como está |
| Etapas sem evento próprio | A entrega do veículo fica no comando genérico "Atualizar status da OS"; relatório e gestão de usuários não aparecem. Início da execução e conclusão estão na área "Ciclo de vida da OS aprovada" (seção 3) | RF-22, RF-27 e RF-03 | Os requisitos e a máquina de estados da Linguagem Ubíqua (§5) prevalecem |
| "Atualizar dados da OS" | Permitido a Gerente e Atendente | Nenhum RF define a atualização dos dados da OS; a Linguagem Ubíqua (§3) dá também ao Mecânico a permissão de atualizar OS | Pendente de decisão do grupo |
| Identificação do cliente | O comando "Entra com credenciais" sugere login | RF-25 e RF-26 dispensam login e exigem número da OS com CPF/CNPJ | Os requisitos prevalecem |
| Histórico de status | Nenhuma área representa o registro das transições no histórico; cada mudança de status aparece como política separada | RF-24 exige um registro imutável de cada transição | Decisão do grupo: o board mantém as atualizações de status separadas, sem política de histórico; o RF-24 prevalece no código |
| Atribuição do mecânico no início da execução | O evento "Serviço iniciado" dispara a política "Atribui mecânico à OS", que gera "Mecânico atribuído" | RF-16 atribui o mecânico no início do diagnóstico, e RF-20 permite iniciar a execução apenas ao mecânico atribuído ou ao Gerente | Os requisitos prevalecem |
| Gerente na abertura e no diagnóstico | "Abrir OS" tem só o Atendente e "Inicia diagnóstico" tem só o Mecânico | RF-13 e RF-16 incluem o Gerente | Os requisitos prevalecem |
| Agregado de estoque | O agregado `EstoquePeca` aparece só na área "Ciclo de vida da OS aprovada"; nas áreas "Criação de ordem de serviço" e "Peças", a reserva e a atualização de saldo não indicam o agregado | A Linguagem Ubíqua (§1) define o agregado `EstoquePeca` | A Linguagem Ubíqua prevalece |
| "Atualizar status da OS" | Comando sem política de permissão | RF-16 a RF-22 definem quem faz cada transição; não há alteração arbitrária de status (RF-23) | A máquina de estados da Linguagem Ubíqua (§5) prevalece |

## 7. Catálogo de Eventos de Domínio

Um evento do board vira classe de evento de domínio quando a regra de um agregado precisa alterar outro agregado (`OrdemServico` → `EstoquePeca` ou `EstoquePeca` → `OrdemServico`). Quando a reação fica dentro do mesmo agregado, o método do agregado executa a reação diretamente, e o evento do board fica registrado só na tabela 7.2.

Os agregados acumulam os eventos, e o caso de uso os entrega ao Event Dispatcher síncrono, que chama os handlers dentro da mesma transação (RNF-08). Um handler pode gerar eventos novos. Por exemplo, o `EstornoPecasHandler` chama `EstoquePeca.estornar`, que emite `SaldoPecaAtualizadoEvent`. Por isso o dispatcher despacha também os eventos gerados durante o despacho, até não restar nenhum.

### 7.1. Eventos com Classe

| Evento | Agregado emissor | Momento da emissão | Consumidor | Evento do board | Requisito |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `OrcamentoFinalizadoEvent` | `OrdemServico` | `finalizar_orcamento`, na transição de `EM_DIAGNOSTICO` para `AGUARDANDO_APROVACAO`; a quantidade de cada `ItemPeca` começa toda pendente | `ReservaPecasHandler`, que, para cada peça da OS, busca as OS com pendência da peça, inclui a OS nova, chama `EstoquePeca.alocar_pendencias` e aplica cada alocação com `OrdemServico.alocar_peca` | Orçamento gerado → Reservar peças | RF-17, RF-18 |
| `OSCanceladaEvent` | `OrdemServico` | `rejeitar_orcamento` e `cancelar(motivo)`, nas transições para `CANCELADA`; o evento leva as quantidades a estornar, calculadas pela OS | `EstornoPecasHandler`, que chama `EstoquePeca.estornar` com as quantidades recebidas no evento | OS reprovada → Estorno de peças; OS cancelada → Estorno de peças | RF-18, RF-23, RF-26 |
| `ExecucaoIniciadaEvent` | `OrdemServico` | `iniciar_execucao`, na transição de `AGUARDANDO_EXECUCAO` para `EM_EXECUCAO`; o evento leva as quantidades reservadas de cada peça | `BaixaEstoqueHandler`, que chama `EstoquePeca.baixar` com as quantidades recebidas no evento | Serviço iniciado → Dar baixa nas peças | RF-20 |
| `SaldoPecaAtualizadoEvent` | `EstoquePeca` | `repor`, `estornar` e `ajustar_quantidade_fisica`, sempre que o saldo disponível aumenta (RF-12) | `AlocacaoPecasPendentesHandler`, que busca as OS com pendência da peça, chama `EstoquePeca.alocar_pendencias` e aplica cada alocação com `OrdemServico.alocar_peca`, que chama `liberar_para_execucao` quando a OS em `AGUARDANDO_PECA` fica sem pendência | Saldo da peça atualizado → Aloca peça pendente nas OS mais antigas | RF-12, RF-18, RF-19 |

Regras de domínio que os handlers apenas acionam:

* **Prioridade pela OS mais antiga (RF-18, RF-19).** `EstoquePeca.alocar_pendencias(pendencias)` recebe as pendências da peça, ordena pela data de abertura da OS, reserva o saldo disponível da mais antiga para a mais nova e devolve as alocações. Os dois handlers usam o mesmo método, por isso a OS nova só recebe saldo depois das OS abertas antes dela. Reservas já feitas não mudam de OS.
* **Estorno e baixa (RF-18, RF-20, RF-23).** A OS só chega a `EM_EXECUCAO` com todas as peças reservadas, e `iniciar_execucao` dá baixa em todas. Por isso a OS cancelada antes de `EM_EXECUCAO` estorna todas as quantidades reservadas, e a OS cancelada em `EM_EXECUCAO` não estorna nada. `cancelar` e `rejeitar_orcamento` calculam essas quantidades a partir do status da OS e as enviam no `OSCanceladaEvent`; o `ItemPeca` não precisa de campo para a quantidade baixada.
* **Ajuste de estoque (RF-12).** `ajustar_quantidade_fisica(nova_quantidade)` corrige a quantidade física (perda, quebra ou inventário). O valor não pode ficar abaixo da quantidade reservada, para que o saldo disponível nunca fique negativo.

Os arquivos seguem a seção 3 de `docs/guia-de-desenvolvimento.md`: os eventos ficam em `src/domain/events/` (ex.: `orcamento_finalizado_event.py`) e os handlers em `src/application/handlers/` (ex.: `reserva_pecas_handler.py`).

### 7.2. Eventos do Board sem Classe

| Evento do board | Método do agregado | Motivo |
| :--- | :--- | :--- |
| OS aberta; Cliente vinculado à OS; Veículo vinculado à OS | Abertura da `OrdemServico` | Nenhum outro agregado reage à abertura |
| Vincula mecânico à OS | `OrdemServico.atribuir_mecanico` | A mudança para `EM_DIAGNOSTICO` acontece no próprio agregado |
| Serviços vinculados; Peças vinculadas | Inclusão de itens na `OrdemServico` | A reserva só acontece na conclusão do orçamento (`OrcamentoFinalizadoEvent`) |
| OS aprovada | `OrdemServico.aprovar_orcamento` | A escolha entre `AGUARDANDO_PECA` e `AGUARDANDO_EXECUCAO` usa as pendências gravadas nos itens da própria OS |
| Baixa de peças utilizadas | `EstoquePeca.baixar` | A baixa não altera o saldo disponível, pois reduz a quantidade física e a reservada na mesma quantidade |
| Saldo da peça atualizado, quando o ajuste reduz a quantidade | `EstoquePeca.ajustar_quantidade_fisica` | A redução diminui o saldo disponível, e nenhuma OS pendente pode ser atendida |
| OS concluída | `OrdemServico.concluir_manutencao` | Nenhum outro agregado reage à conclusão |
| Mudanças de status (Status OS "...") | Métodos de transição da `OrdemServico` | O registro no histórico de status (RF-24) faz parte do agregado `OrdemServico` |
