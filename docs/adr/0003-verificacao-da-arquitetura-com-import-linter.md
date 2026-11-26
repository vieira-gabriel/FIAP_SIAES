# 0003. Verificação da regra de dependência com import-linter

- Status: Aceito
- Data: 2026-11-25
- Requisitos: RNF-01, RNF-02
- Documentos alterados: `docs/requisitos-nao-funcionais.md` (RNF-01), `docs/guia-de-desenvolvimento.md` (seção 8.1, na issue de implementação)

## Contexto e Problema

A regra de dependência da seção 2.1 do guia é verificada hoje só por revisão humana. O enunciado pede evidência da arquitetura escolhida, e a refatoração do [ADR 0002](0002-clean-architecture-leve.md) mexe em todos os routers, o que aumenta a chance de um import proibido passar na revisão.

## Fatores de Decisão

- Falha automática no CI quando uma camada importa outra de forma proibida.
- Mensagem de erro legível, que sirva de evidência no README e no vídeo.
- Pouco código a manter.

## Alternativas Consideradas

| Alternativa | Ganho | Custo |
| :-- | :-- | :-- |
| import-linter | Contratos declarados no `pyproject.toml` (`layers` e `forbidden`), relatório legível, um passo no CI | Uma dependência de desenvolvimento nova; exceções explícitas para `presentation/container.py` e `migrations/env.py` |
| Teste pytest próprio, com varredura de imports por `ast` | Sem dependência nova, roda na suíte existente | Código de varredura a escrever e manter; mensagens de erro menos claras |
| Só revisão humana | Nenhum trabalho | Sem evidência automática; erro passa despercebido |

## Decisão

Usar o import-linter como dependência de desenvolvimento, com os contratos no `pyproject.toml`:

- `domain` não importa `application`, `infrastructure`, `presentation`, nem `fastapi`, `pydantic`, `sqlalchemy`, `asyncpg`, `jwt` ou `bcrypt`.
- `application` não importa `infrastructure` nem `presentation`.
- `infrastructure` não importa `presentation`.
- `presentation` não importa `infrastructure`, com exceção de `presentation.container`.

O comando `uv run lint-imports` entra no job "Lint, testes e segurança" do CI.

## Consequências

- Positivas: a regra de dependência passa a ser verificada em todo PR.
- Negativas: uma dependência a mais no `uv.lock` e no pip-audit.
- Ações: issue da Fase 1 do blueprint; nova linha na seção 8.1 do guia com o link para este ADR.
