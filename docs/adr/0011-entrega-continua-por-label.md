# 0011. Entrega contínua disparada por label

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RNF-06, RNF-19 (novo)
- Documentos alterados: `docs/requisitos-nao-funcionais.md` (RNF-19), `docs/guia-de-desenvolvimento.md` (seções 7 e 8.1, na issue de implementação)

## Contexto e Problema

O enunciado pede uma pipeline com build, testes, build da imagem, deploy no cluster, deploy do banco e aplicação dos manifestos. Os PRs da Fase 2 vão direto para a `main`. O ambiente AWS só existe enquanto o Learner Lab está ligado e o Terraform aplicado, e as credenciais expiram a cada sessão. Um deploy a cada merge falharia sempre que o ambiente estivesse desligado. O custo de crédito vem do tempo em que a infraestrutura fica criada; a execução do deploy em si gasta só minutos do GitHub Actions e alguns MB no ECR.

## Fatores de Decisão

- PRs direto na `main`, mesmo fluxo da Fase 1.
- Deploy apenas quando o grupo quer publicar uma versão e o ambiente está ligado.
- Nenhum segredo no repositório.

## Alternativas Consideradas

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Deploy em todo push na `main` | Fluxo mais simples | Falha sempre que o lab está desligado |
| Tag `v*` e `workflow_dispatch` | Versão explícita, tag da imagem igual à da release | Criação manual da tag |
| Branch `release/*` | Nome explícito | Branch extra a sincronizar; deploy fora da `main` |
| Label `deploy` no PR mesclado | Decisão visível no PR, merge na `main` como sempre | Lógica extra no workflow; risco de esquecer ou pôr a label por engano |
| Marcador na mensagem do commit | Sem passo fora do git | Texto livre, fácil de errar, fora dos prefixos de commit do grupo |

## Decisão

- Workflow `cd.yml`, disparado por `pull_request` do tipo `closed` na `main`, executado só quando o PR foi mesclado e tem a label `deploy`. Também aceita `workflow_dispatch` para reimplantar o commit atual da `main`.
- O job usa o environment `aws`, que guarda `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e `AWS_SESSION_TOKEN` da sessão do lab, os segredos da aplicação (`JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`, `WEBHOOK_API_KEY`) e a variável `DEPLOY_HABILITADO`. Com `DEPLOY_HABILITADO` diferente de `true`, o job termina sem executar os passos e registra o motivo no resumo.
- Passos: build da imagem e push no ECR com a tag igual ao SHA do commit; `aws eks update-kubeconfig`; criação ou atualização do Secret com `kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -`; Job de migration com a nova imagem e espera pela conclusão (deploy do banco); `kubectl apply -k k8s/overlays/aws` com a imagem nova (aplicação dos manifestos); `kubectl rollout status`; smoke test em `GET /health` pelo endereço do Service.
- O CI do PR (lint, testes, cobertura, segurança, build da imagem) continua obrigatório antes do merge; o CD não repete os testes.
- Antes de cada demonstração, o dono do lab atualiza as 3 credenciais no environment `aws`.

## Consequências

- Positivas: a `main` recebe todos os merges; o deploy acontece só quando pedido e com o ambiente ligado.
- Negativas: a credencial temporária exige atualização manual; uma label esquecida deixa o ambiente na versão anterior.
- Ações: label `deploy` criada no repositório (Fase 0 do blueprint); workflow na Fase 5; seção 7 do guia (fluxo de Git) com a regra da label.
