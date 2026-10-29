# Análise de Vulnerabilidades

Análise das dependências, do código-fonte e da imagem Docker exigida pelo RNF-07, com as ferramentas decididas na issue #5 (issue #111).

> Análise feita em 28/10/2026 sobre o commit `a4f2f03` da `main`, com o ajuste do Dockerfile descrito na seção 4.1. **Na entrega, a análise deve ser refeita sobre o commit final**, com os comandos da seção 5, e este relatório atualizado.

## 1. Resultado

| Ferramenta | Versão | Alvo | Crítico | Alto | Médio | Baixo |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| pip-audit | 2.10.1 | 34 dependências de produção (do `uv.lock`, com hashes) e o ambiente completo | 0 | 0 | 0 | 0 |
| Bandit | 1.9.4 | `src/` e `migrations/` (4.124 linhas), em todos os níveis de severidade e confiança | 0 | 0 | 0 | 0 |
| Trivy (`image`) | 0.57.1 | Imagem da aplicação (`python:3.12-slim`, Debian 13.7) | 0 | 44 | 58 | 61 |
| Trivy (`config`) | 0.57.1 | `Dockerfile` | 0 | 0 | 0 | 1 |

**Nenhum achado crítico.** Os achados altos e médios da imagem estão todos em pacotes do sistema operacional da imagem base, **sem correção publicada pelo Debian**, e têm a justificativa da seção 4.2. O achado baixo do `Dockerfile` está justificado na seção 4.3. Além disso, há 1 achado de severidade desconhecida (`UNKNOWN`) na imagem, também sem correção.

## 2. Dependências: pip-audit

Nenhuma vulnerabilidade conhecida nas dependências de produção nem no ambiente de desenvolvimento. O pip-audit já roda no CI em cada PR (`.github/workflows/ci.yml`).

## 3. Código-fonte: Bandit

Nenhum achado em `src/` e `migrations/`, mesmo no nível mais baixo de severidade e de confiança. O Bandit já roda no CI em cada PR.

## 4. Imagem Docker: Trivy

### 4.1. Corrigido: `pip` da imagem base

A primeira varredura apontou 6 vulnerabilidades no `pip 25.0.1` que vem instalado na imagem `python:3.12-slim` (5 médias e 1 baixa: CVE-2025-8869, CVE-2026-13346, CVE-2026-3219, CVE-2026-6357, CVE-2026-8643 e CVE-2026-1703).

A aplicação roda pelo `.venv` criado no estágio de build, que não tem `pip`; o `pip` da imagem base não é usado em tempo de execução. **Correção:** o estágio final do `Dockerfile` desinstala o `pip` antes de trocar para o usuário sem privilégio. A segunda varredura não aponta mais nenhuma vulnerabilidade em pacotes Python. Conferido depois da correção:

- a imagem é construída normalmente;
- os imports da aplicação e o `alembic` funcionam;
- com um PostgreSQL 16, o container aplica as migrations, o `/health` responde `200` e o login do Gerente da carga inicial responde `200`.

### 4.2. Justificado: pacotes do sistema operacional

Os 164 achados restantes estão em pacotes do Debian 13.7 da imagem base. **Nenhum tem versão corrigida publicada** (162 com status `affected` e 2 com `fix_deferred`), então não há atualização a aplicar.

Os 44 achados altos correspondem a **8 CVEs** distintos, repetidos nos vários pacotes que vêm do mesmo código-fonte:

| CVE | Origem | Pacotes afetados | Do que se trata | Por que não afeta a aplicação |
| :--- | :--- | :---: | :--- | :--- |
| CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 | util-linux | 9 | Escalada de privilégio pelos comandos `mount` e `nsenter` | A aplicação não executa `mount` nem `nsenter`, e o container roda com usuário sem privilégio (UID 10001), sem capacidade de montar sistemas de arquivos |
| CVE-2026-54369 | acl | 1 | Escalada de privilégio por symlink nas funções da libacl | A aplicação não manipula ACLs de arquivos, e o código em `/app` pertence ao root, somente leitura para o usuário da aplicação |
| CVE-2025-69720 | ncurses | 4 | Estouro de buffer ao processar dados de terminal | A aplicação é uma API HTTP sem terminal interativo e não usa ncurses |
| CVE-2026-16742 | systemd | 2 | Escalada de privilégio no `systemd-homed` | O container não executa systemd; só as bibliotecas `libsystemd0` e `libudev1` estão na imagem |
| CVE-2026-9538 | perl (Archive::Tar) | 1 | Negação de serviço com arquivo tar malformado | A aplicação não usa Perl nem extrai arquivos tar; o Debian adiou a correção (`fix_deferred`) |

Os 58 achados médios, os 61 baixos e o 1 de severidade desconhecida estão nos mesmos grupos de pacotes de base (`libc6`, `libsystemd0`, `tar`, `coreutils`, `libsqlite3-0`, `passwd`, `perl-base` e outros), todos sem correção publicada, e seguem a mesma justificativa: são utilitários do sistema que a aplicação não executa.

Medidas que reduzem a superfície de ataque da imagem:

- imagem base `slim`, com o mínimo de pacotes do Debian;
- build multi-stage: o `uv`, o cache de build e as ferramentas de desenvolvimento ficam fora da imagem final;
- processo da aplicação com usuário sem privilégio (UID 10001) e código pertencente ao root;
- `pip` removido da imagem final (seção 4.1);
- `.env` e segredos fora da imagem (`.dockerignore`) e lidos do ambiente (RNF-06).

**Acompanhamento:** na reconstrução para a entrega, a imagem base `python:3.12-slim` traz as correções que o Debian tiver publicado até lá, e a nova varredura atualiza esta seção.

### 4.3. Justificado: configuração do `Dockerfile`

O Trivy aprovou 26 das 27 verificações do `Dockerfile`. A única falha é baixa:

| Verificação | Severidade | Justificativa |
| :--- | :--- | :--- |
| AVD-DS-0026: falta a instrução `HEALTHCHECK` | Baixa | O healthcheck do serviço `app` está no `docker-compose.yml`, que é a forma de execução documentada do projeto, e consulta o `/health` |

## 5. Como refazer a análise

Na raiz do projeto, com o Docker em execução. O projeto exige o uv 0.8.22 (`required-version` no `pyproject.toml`); com outra versão instalada, use `uvx uv@0.8.22` no lugar de `uv`.

```bash
# Dependências de produção, exportadas do uv.lock com hashes
uv export --frozen --no-dev --no-emit-project -o requisitos-de-producao.txt
uv run pip-audit -r requisitos-de-producao.txt --require-hashes --disable-pip

# Ambiente completo, com as dependências de desenvolvimento
uv run pip-audit

# Código-fonte
uv run bandit -r src migrations

# Imagem da aplicação
docker build -t siaes:analise .
docker save siaes:analise -o siaes-imagem.tar
docker run --rm -v "$(pwd):/trabalho" aquasec/trivy:0.57.1 image --input /trabalho/siaes-imagem.tar --scanners vuln

# Configuração do Dockerfile
docker run --rm -v "$(pwd):/trabalho" aquasec/trivy:0.57.1 config /trabalho/Dockerfile
```

No Git Bash do Windows, use `MSYS_NO_PATHCONV=1` antes dos comandos `docker run` e `$(pwd -W)` no lugar de `$(pwd)`. Apague o `siaes-imagem.tar` e o `requisitos-de-producao.txt` depois da análise.
