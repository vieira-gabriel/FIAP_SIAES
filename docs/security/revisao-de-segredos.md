# Revisão de Segredos no Código e no Histórico do Git

Verificação do RNF-06: nenhuma credencial, senha, chave ou token pode estar versionado, inclusive no histórico do Git (issue #114).

> Revisão feita em 28/10/2026, sobre o commit `90623dd` da `main` e todas as 40 branches remotas. Na entrega, a varredura deve ser repetida sobre o commit final, com o comando da seção 4.

## 1. Resultado

**Nenhum segredo real encontrado.** Nenhuma troca de credencial foi necessária.

| Verificação | Resultado |
| :--- | :--- |
| Varredura de todo o histórico (todas as branches) com o gitleaks | 2 achados, os dois falsos positivos (seção 2) |
| `.env` em algum commit de qualquer branch | Nunca versionado |
| Outros arquivos `.env*` versionados | Só o `.env.example` |
| Arquivos sensíveis pelo nome (`.pem`, `.key`, `.p12`, `.pfx`, `.crt`, `id_rsa`, `credentials`, dumps de banco) | Nenhum, em todo o histórico |
| Variáveis secretas do `.env.example` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `DEMO_ATENDENTE_PASSWORD`, `DEMO_MECANICO_PASSWORD`) | Vazias nas 4 versões do arquivo no histórico |
| `.gitignore` | Ignora `.env` e `.env.*`, com exceção do `.env.example` |

## 2. Falsos positivos

A regra `generic-api-key` apontou a linha 15 do `.env.example` em dois commits, `3f661de` e `5f3faa7`. Nos dois, a linha é `JWT_SECRET_KEY=`, **sem valor**. O trecho detectado vai da linha 15 até a coluna 24 da linha 16: a regra atravessou a quebra de linha e tomou como segredo a linha seguinte, `JWT_EXPIRATION_HOURS=24`, que é a configuração pública de expiração do token.

Os dois achados estão registrados no `.gitleaksignore`, na raiz do projeto, pela impressão digital do gitleaks (commit, arquivo, regra e linha), para que as próximas varreduras não os reportem de novo. Um segredo real em outra linha, arquivo ou commit continua sendo apontado.

## 3. Valores de teste versionados

Alguns arquivos versionados têm senhas e chaves **de teste**, que não dão acesso a nenhum ambiente real:

| Arquivo | Uso |
| :--- | :--- |
| `.github/workflows/ci.yml` | Banco PostgreSQL efêmero do CI e chave JWT dos testes; o banco só existe durante a execução do workflow |
| `tests/unit/test_config.py`, `tests/unit/test_fluxo_autenticacao.py`, `tests/unit/test_jwt_token_service.py` | Valores fixos dos testes unitários de configuração e de JWT |

A aplicação lê todas as credenciais do ambiente e não inicia sem elas (RNF-06), então nenhum desses valores é usado fora dos testes.

## 4. Como repetir a varredura

Com o Docker em execução, na raiz do projeto, com as branches remotas atualizadas (`git fetch --all`):

```bash
docker run --rm -v "$(pwd):/repo:ro" ghcr.io/gitleaks/gitleaks:v8.21.2 git /repo --log-opts="--all" --redact
```

O gitleaks lê o `.gitleaksignore` da raiz e termina com código `0` quando não há achados novos. No Git Bash do Windows, use `MSYS_NO_PATHCONV=1` antes do comando e `$(pwd -W)` no lugar de `$(pwd)`.

Se um segredo real aparecer: troque a credencial no ambiente onde ela é usada (ela deve ser considerada vazada, mesmo depois de removida do histórico), remova-a do código e registre o procedimento no PR.
