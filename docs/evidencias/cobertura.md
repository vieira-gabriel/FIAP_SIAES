# Evidência de Cobertura de Testes (RNF-14)

A cobertura dos módulos críticos precisa ser de pelo menos **80%** em `src/domain` e em `src/application`. O `source` do `pytest-cov` já está limitado a essas duas pastas em `pyproject.toml` (`[tool.coverage.run]`), então o relatório mede só elas.

## Resultado

Medição feita em 03/11/2026 sobre o commit `a5ca784` (`main` no `f8edaf1` mais o PR desta atualização), com PostgreSQL 16 no ar:

| Pasta | Arquivos | Instruções | Não cobertas | Cobertura |
| :--- | ---: | ---: | ---: | ---: |
| `src/domain` | 43 | 1210 | 0 | **100%** |
| `src/application` | 66 | 1185 | 0 | **100%** |
| **Total** | 109 | 2395 | 0 | **100%** |

1872 testes passando (1249 unitários e 623 de integração), com a meta de 80% atingida (`--cov-fail-under=80`). O relatório completo, arquivo por arquivo, está em [cobertura.txt](cobertura.txt).

## Como reproduzir

Com o `.env` preenchido e o PostgreSQL de testes no ar (guia de desenvolvimento, seção 5.7):

```bash
docker compose -f docker-compose.yml -f docker-compose.testes.yml up -d db
CI=true uv run pytest --cov --cov-report=term-missing --cov-fail-under=80
```

Para o relatório navegável, acrescente `--cov-report=html`; a pasta `htmlcov/` é ignorada pelo Git. O CI executa o mesmo comando com `--cov-fail-under=80` em cada PR e em cada push na `main`, então a meta é verificada continuamente.

## Quando refazer

A cobertura muda a cada merge. Refaça a medição, atualize a tabela acima, o hash do commit e o `cobertura.txt` sobre o commit final da entrega (o informado no PDF).
