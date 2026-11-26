# 0010. State e execução do Terraform

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RNF-06, RNF-18 (novo), RNF-19 (novo)
- Documentos alterados: `docs/requisitos-nao-funcionais.md` (RNF-18), `infra/README.md` (na Fase 4 do blueprint)

## Contexto e Problema

O Terraform da Fase 2 cria recursos que cobram por hora ([ADR 0009](0009-infraestrutura-aws-learner-lab.md)). Vários integrantes e a pipeline precisam ler o mesmo state, e as credenciais do Learner Lab expiram a cada sessão. Um `apply` disparado sem intenção cria um EKS e consome crédito.

## Fatores de Decisão

- State compartilhado e com lock.
- Nenhum recurso criado ou destruído sem decisão explícita.
- Evidência de IaC na pipeline.

## Alternativas Consideradas

| Tema | Alternativa | Ganho | Custo |
| :-- | :-- | :-- | :-- |
| State | S3 com lock nativo (`use_lockfile`, Terraform 1.10 ou superior) | Compartilhado entre integrantes e CI, sem DynamoDB | Bucket criado antes por um bootstrap separado |
| State | Local | Zero configuração | Só quem aplicou consegue alterar ou destruir; risco de recurso esquecido |
| Execução | `fmt`, `validate` e `plan` em PR; `apply` e `destroy` por `workflow_dispatch` | Nenhum EKS criado sem intenção | O vídeo mostra o `apply` disparado à mão |
| Execução | `apply` automático no push | Fluxo totalmente automático | Todo push altera infraestrutura e falha com o lab desligado |
| Execução | `apply` local, CI só `plan` | Menos secrets no GitHub | Evidência na pipeline restrita ao `plan` |

## Decisão

- `infra/bootstrap/`: configuração separada, com state local, que cria só o bucket S3 do state (versionamento ligado, acesso público bloqueado). Executada uma vez por lab.
- `infra/`: configuração principal com backend S3 e `use_lockfile = true`. Versões do Terraform e do provider AWS fixadas.
- Workflow `terraform.yml`: em todo PR que altera `infra/`, executa `terraform fmt -check`, `terraform validate` e, com o environment `aws` habilitado, `terraform plan`. `apply` e `destroy` só por `workflow_dispatch`, com escolha da ação e o environment `aws`.
- `*.tfstate`, `*.tfvars` com segredos e `.terraform/` ficam no `.gitignore`. A senha do RDS vem de variável sensível alimentada por GitHub Secret.
- `infra/README.md` lista os recursos, as variáveis, os comandos (`init`, `plan`, `apply`, `destroy`), o custo por hora e o procedimento de destruição ao fim de cada sessão.

## Consequências

- Positivas: state único, criação e destruição controladas, evidência de IaC em cada PR.
- Negativas: o bucket de state precisa ser recriado se o grupo trocar de lab; o `apply` é manual.
- Ações: Fase 4 e Fase 5 do blueprint.
