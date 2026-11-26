# Registros de Decisão de Arquitetura (ADR)

Esta pasta guarda as decisões de arquitetura do SIAES e as alterações de decisões já documentadas. A regra de quando escrever um ADR está em `AGENTS.md`, seção "Registro de Decisões (ADR)", e a adoção do formato está no [ADR 0001](0001-registro-de-decisoes-em-adr.md).

## Como escrever um ADR

1. Copie o modelo abaixo para `docs/adr/NNNN-titulo-em-kebab-case.md`, com o próximo número livre de 4 dígitos.
2. Preencha todas as seções. Cada alternativa traz o ganho e o custo, com a medida quando ela existir.
3. Acrescente a linha do ADR no índice desta página.
4. Se o ADR altera um RF ou RNF, acrescente ao requisito a observação "Alterado na Fase N" com uma frase sobre a mudança e o link para o ADR.
5. Se o ADR altera uma decisão da seção 8.1 do guia ou uma regra estrutural, registre a entrada em `docs/CHANGELOG.md` com o link para o ADR.
6. Um ADR aceito não é reescrito. Uma decisão nova que o substitui ganha outro número, e o antigo passa ao status "Substituído pelo ADR NNNN".

## Modelo (MADR)

```markdown
# NNNN. Título da decisão

- Status: Proposto | Aceito | Substituído pelo ADR NNNN
- Data: AAAA-MM-DD
- Requisitos: RF-xx, RNF-yy
- Documentos alterados: lista de arquivos

## Contexto e Problema

Qual problema a decisão resolve e por que ele precisa ser decidido agora.

## Fatores de Decisão

- Fator 1 (prazo, custo, requisito do enunciado, restrição técnica).

## Alternativas Consideradas

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| A | ... | ... |
| B | ... | ... |

## Decisão

Alternativa escolhida e a regra que passa a valer.

## Consequências

- Positivas: o que melhora.
- Negativas: o que se perde ou passa a exigir manutenção.
- Ações: issues, documentos ou código que precisam mudar.
```

## Índice

| ADR | Título | Status |
| :-- | :-- | :-- |
| [0001](0001-registro-de-decisoes-em-adr.md) | Registro de decisões em ADR | Aceito |
| [0002](0002-clean-architecture-leve.md) | Clean Architecture leve com DTOs de saída | Aceito |
| [0003](0003-verificacao-da-arquitetura-com-import-linter.md) | Verificação da regra de dependência com import-linter | Aceito |
| [0004](0004-abertura-da-os-com-itens.md) | Abertura da OS com serviços e peças | Aceito |
| [0005](0005-listagem-priorizada-e-paginada.md) | Listagem de OS priorizada, paginada e sem as encerradas | Aceito |
| [0006](0006-status-na-consulta.md) | Status da OS na consulta | Aceito |
| [0007](0007-webhook-de-decisao-do-orcamento.md) | Webhook de decisão do orçamento | Aceito |
| [0008](0008-notificacao-de-status-por-email.md) | Notificação de mudança de status por e-mail | Aceito |
| [0009](0009-infraestrutura-aws-learner-lab.md) | Infraestrutura na AWS Academy Learner Lab | Aceito |
| [0010](0010-terraform-state-e-execucao.md) | State e execução do Terraform | Aceito |
| [0011](0011-entrega-continua-por-label.md) | Entrega contínua disparada por label | Aceito |
| [0012](0012-kubernetes-kustomize-e-hpa.md) | Kubernetes com Kustomize, Job de migration e HPA | Aceito |
