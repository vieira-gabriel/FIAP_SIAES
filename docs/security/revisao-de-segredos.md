# Revisão de Segredos no Código e no Histórico do Git

Verificação do RNF-06: nenhuma credencial, senha, chave ou token pode estar versionado, inclusive no histórico do Git (issue #114).

> Revisão feita em 28/10/2026, sobre a `main`, todas as branches remotas e as referências de pull request (`refs/pull/*/head`), e repetida em 31/10/2026 sobre o commit `cccdc6d` da `main` (merge do PR #160), com 72 branches remotas e 77 referências de PR: 364 commits no histórico, 202 com alterações lidas pelo gitleaks, sem achados além do falso positivo da seção 2. Na entrega, a varredura deve ser repetida sobre o commit final, com o comando da seção 4.

## 1. Resultado

**Nenhum segredo real encontrado.** Nenhuma troca de credencial foi necessária.

| Verificação | Resultado |
| :--- | :--- |
| Varredura de todo o histórico (todas as branches e referências de PR) com o gitleaks | Nenhum achado novo: o único falso positivo (seção 2) está no `.gitleaksignore`, e o comando termina com código `0` |
| Referências de pull request (`refs/pull/*/head`), públicas e fora de um `git fetch` comum | Incluídas na varredura; nenhum achado |
| `.env` em algum commit de qualquer branch | Nunca versionado |
| Outros arquivos `.env*` versionados | Só o `.env.example` |
| Arquivos sensíveis pelo nome (`.pem`, `.key`, `.p12`, `.pfx`, `.crt`, `id_rsa`, `credentials`, dumps de banco) | Nenhum, em todo o histórico |
| Variáveis secretas do `.env.example` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `DEMO_ATENDENTE_PASSWORD`, `DEMO_MECANICO_PASSWORD`) | Vazias em todas as versões do arquivo no histórico (4 versões, conferidas uma a uma) |
| `.gitignore` | Ignora `.env` e `.env.*`, com exceção do `.env.example` |

## 2. Falsos positivos

A regra `generic-api-key` apontou a linha 15 do `.env.example` no commit `5f3faa7`. A linha é `JWT_SECRET_KEY=`, **sem valor**. O trecho detectado vai da linha 15 até a coluna 24 da linha 16: a regra atravessou a quebra de linha e tomou como segredo a linha seguinte, `JWT_EXPIRATION_HOURS=24`, que é a configuração pública de expiração do token.

A varredura feita no clone de quem executou a revisão, que tinha commits ainda não publicados, apontou o mesmo falso positivo também no commit `3f661de`. Esse commit não existe no GitHub (a API responde "No commit found"), então só o `5f3faa7` aparece a quem repete o comando da seção 4. A entrada do `3f661de` continua no `.gitleaksignore`, sem efeito sobre o repositório publicado.

Os achados estão registrados no `.gitleaksignore`, na raiz do projeto, pela impressão digital do gitleaks (commit, arquivo, regra e linha), para que as próximas varreduras não os reportem de novo. Um segredo real em outra linha, arquivo ou commit continua sendo apontado.

## 3. Valores de teste versionados

Alguns arquivos versionados têm senhas e chaves **de teste**, que não dão acesso a nenhum ambiente real:

| Arquivo | Uso |
| :--- | :--- |
| `.github/workflows/ci.yml` | Banco PostgreSQL efêmero do CI e chave JWT dos testes; o banco só existe durante a execução do workflow |
| Arquivos de `tests/unit/` e `tests/integration/` | Valores fixos de teste (senhas de usuários criados nos testes, chave JWT, `senha_hash` fictício), como em `test_config.py`, `test_fluxo_autenticacao.py`, `test_jwt_token_service.py`, `test_fluxo_login.py`, `test_fluxo_usuarios.py` e `conftest.py`. Novos testes seguem a mesma regra: só valores de teste |

A aplicação lê todas as credenciais do ambiente e não inicia sem elas (RNF-06), então nenhum desses valores é usado fora dos testes.

## 4. Como repetir a varredura

Com o Docker em execução, na raiz do projeto, com as branches remotas e as referências de PR atualizadas. As referências de PR são públicas no GitHub e um `git fetch` comum não as traz, por isso entram numa busca à parte:

```bash
git fetch --all
git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'
docker run --rm -v "$(pwd):/repo:ro" ghcr.io/gitleaks/gitleaks:v8.21.2 git /repo --log-opts="--all" --redact
```

O gitleaks lê o `.gitleaksignore` da raiz e termina com código `0` quando não há achados novos. No Git Bash do Windows, use `MSYS_NO_PATHCONV=1` antes do comando e `$(pwd -W)` no lugar de `$(pwd)`.

Se um segredo real aparecer: troque a credencial no ambiente onde ela é usada (ela deve ser considerada vazada, mesmo depois de removida do histórico), remova-a do código e registre o procedimento no PR.
