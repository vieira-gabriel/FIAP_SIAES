# 0009. Infraestrutura na AWS Academy Learner Lab

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RNF-09, RNF-17 (novo), RNF-18 (novo)
- Documentos alterados: `docs/requisitos-nao-funcionais.md` (RNF-17 e RNF-18), `infra/README.md` (na Fase 4 do blueprint)

## Contexto e Problema

O enunciado pede Terraform para o cluster Kubernetes e o banco, e uma pipeline que faça deploy no cluster. Um cluster local não é alcançável pelos runners hospedados do GitHub. O grupo escolheu a AWS e usará a conta da AWS Academy Learner Lab, que tem créditos limitados, credenciais temporárias (sessão de cerca de 4 h) e não permite criar IAM roles nem provedores OIDC: todo recurso que precisa de role usa a `LabRole` já existente.

## Fatores de Decisão

- Cobrir "cluster e banco de dados" no Terraform e "deploy no cluster" na pipeline.
- Funcionar dentro das restrições de IAM do Learner Lab.
- Consumir o mínimo de crédito.

## Alternativas Consideradas

| Tema | Alternativa | Ganho | Custo |
| :-- | :-- | :-- | :-- |
| Conta | Learner Lab | Créditos gratuitos | Sem criação de IAM role, credenciais expiram, ambiente desliga ao fim da sessão |
| Conta | Conta própria | IAM completo, OIDC no CD | Cobrança real no cartão, ~US$ 5 a 8 por dia ligado |
| Cluster | EKS | Kubernetes gerenciado, metrics-server como addon | US$ 0,10/h do control plane e 15 a 20 min de criação |
| Cluster | k3s em EC2 | ~US$ 0,04/h | O grupo mantém o cluster; menos "nuvem gerenciada" |
| Banco | RDS PostgreSQL 16 | Atende "Terraform do banco" de forma explícita | ~US$ 0,017/h e 5 a 10 min de criação |
| Banco | StatefulSet no cluster | Sem custo extra | O Terraform não cria o banco |
| Registry | ECR | Mesma nuvem, criado pelo Terraform | O CD precisa da credencial AWS para o push |
| Registry | GHCR | Autentica com `GITHUB_TOKEN` | `imagePullSecret` no cluster; recurso a menos no Terraform |
| Rede | Subnets públicas para os nós, sem NAT | Economiza ~US$ 1,10/dia | Nós com IP público |
| Rede | Subnets privadas com 1 NAT | Desenho de produção | ~US$ 1,10/dia a mais |
| Exposição | Service `LoadBalancer` | O EKS cria o balanceador sem controller nem IAM extra | ~US$ 0,025/h; HTTP sem TLS |
| Exposição | AWS Load Balancer Controller com Ingress | TLS e roteamento por caminho | Exige IAM role própria (IRSA), indisponível no Learner Lab |
| Exposição | NodePort | Custo zero | IP muda com o nó, porta alta, pouco apresentável |

## Decisão

- Um único Learner Lab, de um integrante, com todos os recursos na região `us-east-1`.
- VPC com 2 zonas de disponibilidade: subnets públicas para os nós do EKS e o balanceador; subnets privadas, sem rota para a internet, para o RDS. Sem NAT Gateway.
- EKS com o papel do cluster e dos nós apontando para a `LabRole`; grupo de nós gerenciado com `t3.medium`, mínimo 2 e máximo 3 nós; addon do metrics-server.
- RDS PostgreSQL 16, `db.t3.micro`, single-AZ, sem acesso público, security group que só aceita conexões dos nós do EKS.
- ECR para a imagem da aplicação.
- API exposta por Service `LoadBalancer`. O ambiente não tem TLS nem domínio próprio; a limitação fica registrada no README.
- Custo estimado com o ambiente ligado: ~US$ 0,23/h (~US$ 5,50/dia). O ambiente é destruído ao fim de cada sessão de trabalho e recriado para a próxima.

## Consequências

- Positivas: cluster e banco gerenciados, criados por código, dentro do crédito.
- Negativas: o deploy depende de alguém iniciar o lab e atualizar as credenciais no GitHub; nós com IP público; tráfego HTTP sem TLS (inclusive a API key do webhook).
- Ações: RNF-17 e RNF-18 novos; Fase 4 do blueprint; state e execução no [ADR 0010](0010-terraform-state-e-execucao.md); CD no [ADR 0011](0011-entrega-continua-por-label.md).
