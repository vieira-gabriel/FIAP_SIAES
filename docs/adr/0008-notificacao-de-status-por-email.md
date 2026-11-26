# 0008. Notificação de mudança de status por e-mail

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RF-29 (novo), RF-24, RF-25, RNF-04, RNF-06, RNF-08, RNF-10
- Documentos alterados: `docs/requisitos-funcionais.md` (RF-29), `docs/guia-de-desenvolvimento.md` (seções 2.2, 3 e 8.1, na issue de implementação), `docs/ddd/linguagem-ubiqua.md` (evento novo)

## Contexto e Problema

O enunciado pede a "atualização de status da OS via alguma ferramenta como e-mail". O texto admite duas leituras: saída (o cliente recebe um e-mail quando o status muda) e entrada (o cliente responde ao e-mail para decidir). A entrada já é coberta pelo webhook do [ADR 0007](0007-webhook-de-decisao-do-orcamento.md). O `EventDispatcher` atual é síncrono e roda dentro da transação: um envio de e-mail ali faria uma falha do servidor SMTP desfazer a transição da OS e somaria a latência do SMTP à resposta.

## Fatores de Decisão

- Falha de e-mail não pode desfazer nem atrasar a transição da OS (RNF-08, RNF-10).
- Demonstração visível no vídeo, sem custo e sem verificação de domínio.
- Evitar injeção de conteúdo com textos digitados (RNF-04).

## Alternativas Consideradas

Leitura do enunciado:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Saída: notificar o cliente | Simples, testável com Mailpit | Não cobre resposta por e-mail (coberta pelo webhook) |
| Entrada: cliente responde ao e-mail | Literal na outra leitura | Caixa postal, parsing de texto livre e muito mais trabalho |

Momento do envio:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| `BackgroundTasks` do FastAPI após o commit | Envio depois da resposta, sem somar latência ao p95 | E-mail perdido se o pod cair entre a resposta e o envio; só o log registra |
| `await` após o commit, antes da resposta | Mais simples de testar | Latência do SMTP em toda transição |
| Outbox com worker | Nenhum e-mail perdido, reenvio automático | Migration, worker ou CronJob e testes novos |

Status que enviam:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Todas as transições | Regra única | Até 7 e-mails por OS, inclusive transições internas |
| Só as relevantes ao cliente | Menos e-mails | Lista de status a manter no domínio |

Provedor:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Mailpit no compose e no cluster | Custo zero, sem verificação de domínio, interface web para o vídeo | Nenhum e-mail sai de verdade |
| Amazon SES | Entrega real | Sandbox exige e-mails verificados; o Learner Lab pode restringir; IAM a mais |

Formato:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Texto puro | Sem risco de injeção de HTML, sem biblioteca de template | Aparência simples |
| HTML e texto | Aparência melhor | Escape obrigatório em todos os campos e testes de segurança |

## Decisão

- Notificação de saída. Os status de destino que enviam e-mail são `AGUARDANDO_APROVACAO`, `EM_EXECUCAO`, `FINALIZADA` e `CANCELADA`.
- `OrdemServico._mudar_status` acumula um evento novo, `StatusOSAlteradoEvent` (id e número da OS, status anterior e novo, momento), só para esses 4 status de destino. A lista fica no domínio.
- Esse evento não passa pelo `EventDispatcher` transacional. O caso de uso devolve os eventos de notificação junto com o resultado, e a rota agenda o envio com `BackgroundTasks` depois que a unidade de trabalho confirma a transação. Uma transação desfeita não envia nada.
- Porta `NotificadorDeStatus` em `application/ports/`; caso de uso `NotificarClienteDaMudancaDeStatus` em `application/use_cases/`, que lê a OS e o cliente e monta a mensagem; adaptador `SmtpNotificadorDeStatus` em `infrastructure/notificacoes/`, com o `smtplib` da biblioteca padrão executado por `asyncio.to_thread`, sem dependência nova.
- Falha de envio é registrada em log com o número da OS e o status, sem dados pessoais nem stack trace na resposta. Não há nova tentativa.
- Corpo em texto puro, com o número da OS, o status novo em linguagem do cliente, o valor total (em `AGUARDANDO_APROVACAO`), o motivo (em `CANCELADA`) e o link `URL_PUBLICA/cliente/#numero=<numero>`. O documento do titular nunca vai no e-mail nem na URL.
- Variáveis novas: `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA` (opcionais no Mailpit), `EMAIL_REMETENTE`, `URL_PUBLICA`.
- Mailpit no `docker-compose.yml` e no cluster (local e AWS). Na AWS, a interface do Mailpit é acessada por `kubectl port-forward`, sem Service público.

## Consequências

- Positivas: item 6 do enunciado atendido sem afetar a transação nem o tempo de resposta.
- Negativas: e-mail pode se perder em queda do pod; nenhum e-mail real sai do ambiente AWS.
- Ações: RF-29 novo; porta e adaptador na tabela da seção 2.2 do guia; pasta `infrastructure/notificacoes/` na seção 3; evento novo na Linguagem Ubíqua; issue da Fase 2 do blueprint.
