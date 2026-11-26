# 0007. Webhook de decisão do orçamento

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RF-28 (novo), RF-24, RF-26, RNF-03, RNF-06, RNF-08
- Documentos alterados: `docs/requisitos-funcionais.md` (RF-28), `docs/guia-de-desenvolvimento.md` (seções 5.5, 5.6 e 8.1, na issue de implementação)

## Contexto e Problema

O enunciado pede um endpoint que receba notificações externas de aprovação ou recusa do orçamento. As rotas atuais de decisão exigem o documento do titular (`POST /acompanhamento/aprovacao` e `/rejeicao`, RF-26) ou o JWT de um funcionário (decisão no balcão). Um sistema externo (portal, aplicativo de mensagens, gateway de pagamento) não tem nenhum dos dois e pode reenviar a mesma notificação.

## Fatores de Decisão

- Autenticação do remetente sem JWT de usuário.
- Idempotência: a mesma notificação recebida duas vezes não pode gerar efeito duplicado nem erro.
- Reaproveitar as regras de aprovação e rejeição existentes, com o estorno das reservas na mesma transação (RNF-08).
- Facilidade de demonstrar no Swagger, no Postman e no vídeo.

## Alternativas Consideradas

Autenticação:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| API key no header `X-API-Key` | Fácil de demonstrar e de configurar no Secret do Kubernetes | A chave trafega em cada requisição; integridade do corpo depende do HTTPS |
| HMAC do corpo | Integridade e autenticidade, padrão de mercado | O integrador e o vídeo precisam calcular a assinatura; o Swagger não faz isso sozinho |
| HMAC com timestamp | Proteção contra reenvio | Maior esforço e demonstração mais complexa |

Identificação da OS:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Só `numero_os` | Contrato simples para um remetente autenticado | Quem tiver a chave decide qualquer OS |
| `numero_os` e documento | Segunda barreira, igual à rota pública | O integrador precisa do CPF/CNPJ, o que o enunciado não pede |

Idempotência:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Tabela de notificações recebidas | Reenvio devolve a resposta original; trilha de auditoria | Migration, porta e adaptador novos |
| Pelo estado da OS | Nenhum código novo | Reenvio legítimo recebe `422`; idempotência fraca |

Origem no histórico (RF-24):

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| `CLIENTE` | Sem mudança no enum nem no banco | O histórico não distingue o canal; a tabela de notificações guarda essa diferença |
| Nova origem `INTEGRACAO` | Histórico mostra o canal | Enum, migration, Linguagem Ubíqua e testes alterados |

Conflito de `id_notificacao` (mesmo id com outra OS ou outra decisão):

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| `422` com código `NOTIFICACAO_DIVERGENTE` | Usa a lista de códigos do guia (seção 5.5) | Semântica de conflito menos explícita que um `409` |
| `409 Conflict` | Semântica HTTP exata | Código novo na lista do guia, no tratamento de erros e no OpenAPI |

## Decisão

- Rota `POST /webhooks/orcamento`, sem JWT, autenticada pelo header `X-API-Key`. A chave vem da variável `WEBHOOK_API_KEY` (Secret no Kubernetes, `.env` no local) e é comparada em tempo constante (`hmac.compare_digest`). Chave ausente ou errada responde `401` (`NAO_AUTENTICADO`). A subida da aplicação falha sem a variável.
- Corpo: `{"id_notificacao": "texto de 1 a 100 caracteres", "numero_os": "...", "decisao": "APROVADO" | "RECUSADO"}`.
- `APROVADO` chama a mesma regra do `AprovarOrcamento`; `RECUSADO` chama a do `RejeitarOrcamento`, com o `OSCanceladaEvent` e o estorno na mesma transação e a repetição em impasse.
- A OS é localizada só pelo número. Número inexistente ou malformado responde `404` (`ENTIDADE_NAO_ENCONTRADA`); OS fora de `AGUARDANDO_APROVACAO` responde `422` (`REGRA_DE_NEGOCIO_VIOLADA`).
- O histórico grava a origem `CLIENTE`, sem usuário.
- Tabela `notificacoes_orcamento` (id da notificação como chave única, número da OS, decisão, momento do recebimento e status resultante), gravada na mesma transação da decisão. Porta `NotificacaoOrcamentoRepository` no domínio e adaptador Postgres.
- Reenvio com o mesmo `id_notificacao`, a mesma OS e a mesma decisão responde `200` com a resposta original, sem efeito novo. O mesmo `id_notificacao` com OS ou decisão diferentes responde `422` com o código `NOTIFICACAO_DIVERGENTE`.
- Resposta `200`: `{"numero_os", "status", "id_notificacao", "processada_em"}`.
- A rota não usa o limite público do SlowAPI, porque a autenticação pela chave já restringe o acesso.

## Consequências

- Positivas: item 4 do enunciado atendido com idempotência real e as regras de decisão reaproveitadas.
- Negativas: a segurança da rota depende do sigilo da chave e do transporte (o ambiente AWS não tem TLS, limitação registrada no [ADR 0009](0009-infraestrutura-aws-learner-lab.md)).
- Ações: RF-28 novo; nova linha `NOTIFICACAO_DIVERGENTE` e regra da API key nas seções 5.5 e 5.6 do guia; issue da Fase 2 do blueprint.
