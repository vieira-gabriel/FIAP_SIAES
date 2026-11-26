# 0002. Clean Architecture leve com DTOs de saída

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RNF-01, RNF-02 (alterado)
- Documentos alterados: `docs/requisitos-nao-funcionais.md` (RNF-01), `docs/guia-de-desenvolvimento.md` (seções 2, 3 e 5, nas issues da Fase 1 do blueprint), `docs/estrutura-de-pastas.md`, `docs/ddd/c4-model.md`

## Contexto e Problema

O enunciado da Fase 2 exige a refatoração com Clean Architecture ou Arquitetura Hexagonal. O código da Fase 1 já segue a regra de dependência para dentro (`domain`, `application`, `infrastructure`, `presentation`), mas as rotas montam as respostas a partir das entidades do domínio: há 27 chamadas de `de_entidade` em `presentation/routers/`, e só alguns casos de uso devolvem objetos próprios (`DetalheDaOrdemServico`, `ResumoDaOrdemServico`, `CriteriosDaListagem`), definidos dentro do arquivo do caso de uso. A apresentação conhece o interior do domínio, o que a Clean Architecture proíbe na fronteira.

## Fatores de Decisão

- Prazo de 8 semanas, com a infraestrutura (Kubernetes, Terraform, CD) como a parte mais arriscada.
- Valor percebido da refatoração pelo avaliador.
- Risco de conflito entre PRs paralelos.

## Alternativas Consideradas

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| Clean leve: mantém as 4 pastas e cria `application/dtos/`, `presentation/controllers/` e `presentation/presenters/` | 0 arquivos movidos, sem congelar merges; a infraestrutura começa logo | O README precisa explicar o mapeamento das pastas para os círculos |
| Clean completa: pastas `interface_adapters/`, `infrastructure/web/` e `main/` | Uma pasta por círculo, leitura direta pelo avaliador | ~61 arquivos movidos, ~170 linhas de import reescritas, +3 a 5 dias-pessoa e 2 a 3 dias de merges congelados; os repositórios Postgres em `interface_adapters/` importariam SQLAlchemy |
| Hexagonal completa | Portas de entrada e saída explícitas, encaixe natural do webhook e do e-mail | Mesmo volume de movimentação da Clean completa e cerca de 54 interfaces de entrada |
| Hexagonal com poucas portas de entrada | Menos cerimônia que a completa | Movimentação de pastas igual; portas de entrada parciais podem ser vistas como decorativas |

Comparação detalhada em `docs/fase2/PLANEJAMENTO-FASE-2.md`, partes D, E e F.

## Decisão

Clean Architecture leve, com DTOs de saída em todos os 54 casos de uso.

- Os casos de uso recebem DTOs de entrada ou objetos de valor e devolvem DTOs de saída (dataclasses imutáveis em `application/dtos/`, um arquivo por recurso). Nenhum caso de uso devolve entidade.
- Os DTOs que hoje ficam dentro dos arquivos dos casos de uso (`DetalheDaOrdemServico`, `ResumoDaOrdemServico`, `CriteriosDaListagem`) passam para `application/dtos/`.
- `presentation/controllers/` converte o corpo da requisição (schema Pydantic) no DTO de entrada, com os objetos de valor (`Documento`, `Placa`).
- `presentation/presenters/` converte o DTO de saída no schema de resposta. Os métodos `de_entidade` saem dos schemas.
- Os routers ficam finos: recebem a requisição, chamam o controller, o caso de uso e o presenter.
- A migração é feita um router por PR, com a suíte da Fase 1 verde em cada PR.

Mapeamento das pastas para os círculos: `domain/` é o círculo 1 (Enterprise Business Rules); `application/` é o círculo 2 (Application Business Rules); `presentation/` e `infrastructure/repositories/` formam o círculo 3 (Interface Adapters); `infrastructure/database/`, `infrastructure/security/`, `infrastructure/config.py` e o FastAPI formam o círculo 4 (Frameworks & Drivers); `presentation/container.py` é o ponto de composição.

## Consequências

- Positivas: a fronteira HTTP deixa de conhecer as entidades; o padrão vale para os casos de uso novos da Fase 2.
- Negativas: cerca de 10 PRs de migração e ajuste dos testes de rota; mais um arquivo por recurso em `application/dtos/` e em `presentation/presenters/`.
- Ações: RNF-01 recebe a observação de alteração; o guia ganha as linhas de `application/dtos/`, `presentation/controllers/` e `presentation/presenters/` na seção 3 e a receita da seção 5.4 passa a devolver DTO; a verificação automática fica no [ADR 0003](0003-verificacao-da-arquitetura-com-import-linter.md).
