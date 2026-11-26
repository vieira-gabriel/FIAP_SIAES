# 0005. Listagem de OS priorizada, paginada e sem as encerradas

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RF-14 (alterado), RNF-10
- Documentos alterados: `docs/requisitos-funcionais.md` (RF-14), `docs/guia-de-desenvolvimento.md` (seção 8.1, decisão "Listagem de OS", na issue de implementação)

## Contexto e Problema

O enunciado pede a listagem ordenada por status (Em Execução > Aguardando Aprovação > Diagnóstico > Recebida), com as mais antigas primeiro, e sem as OS finalizadas e entregues. A listagem da Fase 1 (RF-14) ordena da abertura mais recente para a mais antiga (`ORDER BY data_abertura DESC` em `PostgresOrdemServicoRepository`), mostra todos os status e não tem paginação. O enunciado cita 4 status, e o sistema tem 9.

## Fatores de Decisão

- Atender o item 5 do enunciado literalmente nos 4 status citados.
- Posicionar os 5 status que o enunciado não cita com um critério explicável.
- Desempenho com o volume de várias unidades (RNF-10).

## Alternativas Consideradas

Posição de `AGUARDANDO_EXECUCAO` e `AGUARDANDO_PECA`:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Logo após `EM_EXECUCAO` | OS já aprovadas ficam perto das que estão em execução, coerente com a fila de execução | Status não citados pelo enunciado ficam no topo; exige justificativa documentada |
| No fim, após `RECEBIDA` | Os 4 status do enunciado ficam no topo na ordem pedida | OS aprovadas esperando execução ficam abaixo das recém-abertas |

Encerradas (`FINALIZADA`, `ENTREGUE`, `CANCELADA`):

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Saem da listagem sem filtro; aparecem com `status` explícito | Sem parâmetro novo | Ver todas as encerradas juntas exige uma consulta por status |
| Parâmetro `incluir_encerradas` | Tudo em uma chamada | Parâmetro a mais no contrato e nos testes |
| Nenhuma forma de ver | Contrato mais simples | Quadro e relatórios perdem acesso às encerradas pela listagem |
| Excluir só `FINALIZADA` e `ENTREGUE` (literal) | Igual ao texto do enunciado | OS canceladas ocupam a lista de trabalho sem ação possível |

Paginação:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| `limit`/`offset` | Simples, combina com o `ORDER BY CASE` | Muda o formato da resposta, a tela do quadro e os testes da Fase 1 |
| Sem paginação | Contrato mantido | Resposta cresce sem limite |
| Cursor (keyset) | Desempenho estável em volumes grandes | Cursor composto (prioridade, data, id) e testes maiores |

## Decisão

- Ordem de prioridade: `EM_EXECUCAO`, `AGUARDANDO_EXECUCAO`, `AGUARDANDO_PECA`, `AGUARDANDO_APROVACAO`, `EM_DIAGNOSTICO`, `RECEBIDA`. Dentro do mesmo status, `data_abertura` ascendente e, no empate, `id`.
- A ordem de prioridade é regra de negócio e fica no domínio, em um objeto de valor (`PrioridadeStatusOS`); o adaptador Postgres a traduz em `ORDER BY CASE`, para a ordenação funcionar com a paginação.
- Sem o filtro `status`, a listagem exclui `FINALIZADA`, `ENTREGUE` e `CANCELADA`. Com `status` informado, a listagem devolve as OS daquele status, inclusive as encerradas.
- Paginação por `limit` (padrão 50, máximo 200) e `offset` (padrão 0). Valor fora da faixa é recusado na validação dos parâmetros da rota, com `422` (`ENTRADA_INVALIDA`). A resposta passa a ser `{"itens": [...], "total": int, "limit": int, "offset": int}`.
- Os demais filtros do RF-14 continuam combináveis.

## Consequências

- Positivas: item 5 do enunciado atendido e resposta limitada em tamanho.
- Negativas: contrato da resposta muda (lista vira objeto); a tela do quadro de OS e os testes de listagem da Fase 1 precisam de ajuste.
- Ações: observação de alteração no RF-14; issue da Fase 2 (API) e da Fase 8 (interface) do blueprint.
