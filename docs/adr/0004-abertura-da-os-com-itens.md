# 0004. Abertura da OS com serviços e peças

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RF-13 (alterado), RF-17 (alterado), RF-21, RNF-08
- Documentos alterados: `docs/requisitos-funcionais.md` (RF-13 e RF-17), `docs/ddd/linguagem-ubiqua.md` e `docs/guia-de-desenvolvimento.md` (seção 8.1, decisões "Abertura da OS" e "Itens e conclusão do orçamento", nas issues de implementação)

## Contexto e Problema

O enunciado pede que a abertura da OS receba os dados do cliente, do veículo, dos serviços e das peças e devolva a identificação única da OS. Hoje `POST /ordens-servico` recebe só o documento e a placa (com os dados de cliente e veículo novos), e os itens entram depois, por rotas próprias, e só em `EM_DIAGNOSTICO` (`OrdemServico._exigir_itens_editaveis`).

## Fatores de Decisão

- Atender o item 2 do enunciado sem quebrar o contrato da Fase 1.
- Manter a máquina de estados, a atribuição do mecânico (RF-16) e o diagnóstico.
- Abertura atômica (RNF-08).

## Alternativas Consideradas

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Estender `POST /ordens-servico` com itens opcionais; a OS nasce em `RECEBIDA` com os itens | Contrato compatível; o mecânico revisa os itens no diagnóstico e conclui o orçamento | A regra de inclusão passa a aceitar `RECEBIDA` (entidade, testes e RF-17) |
| Nova rota composta | Contrato antigo intocado | Duas rotas de abertura para manter e documentar |
| OS nasce em `AGUARDANDO_APROVACAO` com orçamento | Abertura já devolve o orçamento | Pula `RECEBIDA` e `EM_DIAGNOSTICO`, cria transição sem mecânico, conflita com RF-16 e RF-17 |
| Escolha do atendente por campo no corpo | Cobre os dois casos | Dois caminhos de abertura para testar e documentar |

Identificação dos itens:

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Por id (UUID) | Igual às rotas de itens atuais (`servico_id`, `peca_id`); reaproveita a lógica existente sem conversão | O integrador consulta `/servicos` e `/pecas` antes |
| Por código | Código legível para integração | Novos métodos `buscar_por_codigo` nas portas e dois contratos diferentes |
| Aceitar os dois | Flexibilidade | Validação de exclusividade e mais testes |

## Decisão

- `POST /ordens-servico` aceita os campos opcionais `servicos: [{"servico_id": UUID}]` e `pecas: [{"peca_id": UUID, "quantidade": int}]`.
- A OS nasce em `RECEBIDA`, com os itens incluídos. Não há cálculo de orçamento nem reserva de peça na abertura; isso continua na conclusão do orçamento (RF-17, RF-18).
- A inclusão e a remoção de itens passam a valer em `RECEBIDA` e em `EM_DIAGNOSTICO`. A partir de `AGUARDANDO_APROVACAO` os itens continuam bloqueados (`ItensBloqueados`, `422`).
- As regras de inclusão existentes continuam: só serviço e peça ativos, uma vez cada, quantidade inteira positiva. Item inválido responde como as rotas de itens (`404` para inexistente, `422` para excluído ou repetido, `400` para quantidade não positiva).
- Cliente, veículo, OS e itens são gravados na mesma unidade de trabalho; qualquer falha desfaz tudo (RNF-08).
- A resposta continua `201` com o `id` (UUID) e o `numero` da OS, e passa a trazer os itens.

## Consequências

- Positivas: item 2 do enunciado atendido com o contrato antigo válido (corpo sem itens continua funcionando).
- Negativas: a regra "itens só em `EM_DIAGNOSTICO`" da Fase 1 muda; testes unitários e de integração dessa regra precisam ser ajustados.
- Ações: observação de alteração no RF-13 e no RF-17; Linguagem Ubíqua (§5, edição de itens); issue da Fase 2 do blueprint.
