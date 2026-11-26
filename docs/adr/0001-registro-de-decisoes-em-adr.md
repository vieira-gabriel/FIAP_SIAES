# 0001. Registro de decisões em ADR

- Status: Aceito
- Data: 2026-11-25
- Requisitos: nenhum (regra de processo)
- Documentos alterados: `AGENTS.md`, `docs/guia-de-desenvolvimento.md` (seções 1, 3 e 9), `docs/estrutura-de-pastas.md`, `docs/CHANGELOG.md`

## Contexto e Problema

Na Fase 1, as decisões técnicas ficaram na tabela da seção 8.1 do guia e o motivo de cada mudança estrutural ficou no `docs/CHANGELOG.md`. A tabela guarda só a decisão vigente, sem as alternativas descartadas e seus custos, e o CHANGELOG não registra mudanças de requisito. A Fase 2 altera requisitos da Fase 1 (RF-13, RF-14, RF-17, RNF-01, RNF-05 e RNF-15) e toma decisões de infraestrutura que precisam de justificativa para o avaliador e para quem implementa as issues.

## Fatores de Decisão

- Rastreabilidade de cada requisito alterado até o motivo da alteração.
- Registro das alternativas descartadas com ganho e custo (regra de trade-off do grupo).
- Pouco trabalho de manutenção, com os documentos da Fase 1 preservados.

## Alternativas Consideradas

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| ADR no formato MADR em `docs/adr/` | Seção própria de alternativas com ganho e custo; um arquivo por decisão, fácil de linkar nas issues | ~40 a 60 linhas por ADR |
| ADR no formato Nygard | Modelo curto, ~20 linhas | Alternativas e custos sem seção própria |
| Manter só a seção 8.1 e o CHANGELOG | Nenhum documento novo | Sem alternativas descartadas e sem registro das mudanças de requisito |
| ADR substitui o CHANGELOG e a seção 8.1 | Fonte única das decisões | Reescrever dezenas de decisões da Fase 1, trabalho sem ganho de nota |

## Decisão

Adotar ADRs no formato MADR em `docs/adr/`, numerados com 4 dígitos, com o modelo e o índice em `docs/adr/README.md`.

- Toda decisão de arquitetura nova e toda alteração de uma decisão já documentada (requisito, seção 8.1 do guia, estrutura de pastas, regra de processo) gera um ADR.
- O RF ou RNF alterado recebe a observação "Alterado na Fase N", com uma frase simples sobre a mudança e o link para o ADR.
- A seção 8.1 do guia continua como resumo das decisões vigentes, e cada linha nova ou alterada traz o link para o ADR.
- O `docs/CHANGELOG.md` continua como linha do tempo das mudanças estruturais, e cada entrada nova traz o link para o ADR.

## Consequências

- Positivas: cada requisito alterado aponta para o motivo; as issues da Fase 2 citam o ADR da decisão.
- Negativas: uma decisão pode exigir atualização em três lugares (ADR, seção 8.1 e CHANGELOG).
- Ações: regra registrada em `AGENTS.md`; pasta `docs/adr/` registrada no guia (seções 1, 3 e 9) e em `docs/estrutura-de-pastas.md`.
