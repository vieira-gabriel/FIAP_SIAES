# 0012. Kubernetes com Kustomize, Job de migration e HPA

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RNF-05 (alterado), RNF-06, RNF-15 (alterado), RNF-17 (novo)
- Documentos alterados: `docs/requisitos-nao-funcionais.md` (RNF-05, RNF-15 e RNF-17), `docs/guia-de-desenvolvimento.md` (seções 3 e 8.1, nas issues de implementação), `k8s/README.md` (na Fase 3 do blueprint)

## Contexto e Problema

O enunciado pede manifestos com Deployments, Services, ConfigMaps, Secrets e HPA por CPU e memória, que rodem em um cluster local para desenvolvimento e no EKS. Três comportamentos da Fase 1 mudam com várias réplicas: o `CMD` do Dockerfile roda `alembic upgrade head` antes do Uvicorn (várias réplicas correriam a migration ao mesmo tempo); o SlowAPI conta as requisições em memória por processo; e os segredos estão no `.env`.

## Fatores de Decisão

- YAML legível pelo avaliador, sem ferramenta nova.
- Mesma base de manifestos para o cluster local e o EKS.
- Migration executada uma vez por deploy.
- Escala visível no vídeo com o cenário do Locust já existente.

## Alternativas Consideradas

| Tema | Alternativa | Ganho | Custo |
| :-- | :-- | :-- | :-- |
| Variação local × AWS | Kustomize `base` e overlays | Embutido no `kubectl` (`apply -k`), YAML puro | Patches para as diferenças |
| Variação local × AWS | Helm | Valores parametrizados e rollback por release | Linguagem de template; manifestos menos diretos para o avaliador |
| Cluster local | Kubernetes do Docker Desktop | Nada a instalar; imagem local visível sem `image load`; `LoadBalancer` em `localhost` | metrics-server mantido como manifesto no overlay; versão do Kubernetes fixa pela versão do Docker Desktop |
| Cluster local | minikube | Versão do Kubernetes escolhida; metrics-server por addon | Instalação separada, ~2 GB de RAM a mais, passos `minikube image load` e `minikube tunnel` |
| Cluster local | kind | Leve e rápido | metrics-server com `--kubelet-insecure-tls` e `kind load` a cada build |
| Migration | Job antes do rollout | Executa uma vez por deploy; falha visível no pipeline | `CMD` do Dockerfile muda; o compose ganha um serviço de migration |
| Migration | initContainer | O pod nunca sobe sem schema | Cada réplica e cada escala do HPA rodam o Alembic |
| Segredos | Criados pela pipeline a partir dos GitHub Secrets | Nenhum segredo no git | No local, cada integrante cria o Secret a partir do `.env` |
| Segredos | AWS Secrets Manager com External Secrets | Gestão na nuvem | Exige IAM role própria, indisponível no Learner Lab |
| HPA | CPU 60% e memória 80%, 2 a 6 réplicas | Alta disponibilidade e escala visível | Até 6 pods nos nós; memória em Python pode segurar réplicas após a carga |
| HPA | Só CPU 60%, 2 a 6 | Escala previsível | O enunciado cita CPU e memória |
| HPA | CPU 70%, 1 a 4 | Menos nós | 1 réplica contradiz a alta disponibilidade |
| Rate limit | Documentar o limite por pod | Nenhum código ou infraestrutura nova | Limite efetivo vira 10/min vezes o número de pods |
| Rate limit | Redis compartilhado | Limite global correto | Redis no compose e no cluster, 1 a 2 dias de trabalho |

## Decisão

- Estrutura:

```text
k8s/
├── base/                  namespace, configmap, secret.example, deployment e service da API, hpa, job de migration, mailpit
├── overlays/
│   ├── local/             Docker Desktop: Postgres em StatefulSet com PVC, metrics-server, imagem local
│   └── aws/               imagem do ECR, endpoint do RDS no ConfigMap, Service LoadBalancer
└── README.md
```

- Cluster local: Kubernetes do Docker Desktop. O overlay `local` inclui o manifesto do metrics-server com `--kubelet-insecure-tls`.
- Deployment da API com `requests` e `limits` de CPU e memória (o HPA depende dos `requests`), `readinessProbe` e `livenessProbe` em `/health`, e usuário não-root.
- HPA `autoscaling/v2` com CPU a 60% e memória a 80% de utilização média, mínimo 2 e máximo 6 réplicas.
- O `CMD` do Dockerfile passa a executar só o Uvicorn. A migration roda em um Job (`alembic upgrade head`) antes do rollout da API, no CD e no overlay local; o `docker-compose.yml` ganha um serviço `migration` do qual a `app` depende.
- O Secret real nunca vai para o git: `k8s/base/secret.example.yaml` mostra as chaves; o CD cria o Secret a partir dos GitHub Secrets; no local, o `k8s/README.md` documenta o comando que cria o Secret a partir do `.env`.
- O limite do SlowAPI passa a valer por pod. A limitação fica registrada no RNF-05, no guia e no README.

## Consequências

- Positivas: mesma base para o local e o EKS; migration única por deploy; escala demonstrável com o Locust.
- Negativas: o limite público efetivo cresce com o número de réplicas; cada integrante mantém o próprio Docker Desktop com Kubernetes ligado.
- Ações: observação de alteração no RNF-05 e no RNF-15; RNF-17 novo; Fases 3 e 5 do blueprint.
