# 0006. Status da OS na consulta

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RF-15, RF-25
- Documentos alterados: `README.md` (tabela de correspondência, na Fase 6 do blueprint), descrição das rotas no OpenAPI

## Contexto e Problema

O enunciado pede a consulta de status com 6 valores (Recebida, Diagnóstico, Aguardando Aprovação, Execução, Finalizada, Entregue). O sistema tem 9 status (Linguagem Ubíqua §5) e já oferece duas consultas: `POST /acompanhamento` (pública, número da OS e documento do titular) e `GET /ordens-servico/{id}` (autenticada).

## Fatores de Decisão

- Não perder informação que o cliente e a oficina já usam (peça pendente, cancelamento).
- Não criar rota sem necessidade.
- Deixar o item 3 do enunciado fácil de encontrar para o avaliador.

## Alternativas Consideradas

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Manter os 9 status e documentar a correspondência | Contrato sem mudança, nenhum dado perdido | O avaliador lê a tabela no README e no Swagger |
| Campo extra `status_resumido` com os 6 valores | Resposta traz os dois | Mapeamento novo, mudança de DTO e testes; `CANCELADA` e `AGUARDANDO_PECA` sem par direto |
| Só os 6 do enunciado | Contrato literal | Perde informação, quebra a página do cliente e os testes da Fase 1 |
| Rota nova `GET /ordens-servico/{id}/status` | Nome direto no Swagger | Caso de uso, DTO, rota e testes novos (~1 dia) para dados que as rotas atuais já devolvem |

## Decisão

- Nenhuma rota nova. A consulta de status é atendida por `POST /acompanhamento` (cliente) e `GET /ordens-servico/{id}` (oficina).
- A API continua com os 9 status. O README e a descrição das duas rotas no OpenAPI trazem a correspondência:

| Status do enunciado | Status do sistema |
| :-- | :-- |
| Recebida | `RECEBIDA` |
| Diagnóstico | `EM_DIAGNOSTICO` |
| Aguardando Aprovação | `AGUARDANDO_APROVACAO` |
| Execução | `AGUARDANDO_PECA`, `AGUARDANDO_EXECUCAO`, `EM_EXECUCAO` |
| Finalizada | `FINALIZADA` |
| Entregue | `ENTREGUE` |
| (não citado) | `CANCELADA` |

## Consequências

- Positivas: zero código; contrato da Fase 1 preservado.
- Negativas: o avaliador depende da documentação para ligar o item 3 às rotas existentes.
- Ações: tabela no README (Fase 6 do blueprint) e nas descrições do OpenAPI (Fase 2 do blueprint).
