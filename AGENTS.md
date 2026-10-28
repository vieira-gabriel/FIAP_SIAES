# Instruções para Assistentes de IA

Antes de criar ou alterar qualquer arquivo neste repositório, leia `docs/guia-de-desenvolvimento.md`. Ele define onde cada parte do código fica, a regra de dependência entre camadas e as convenções do projeto. A seção 9 do guia contém as regras específicas para assistentes de IA.

## Clean Code

Toda implementação segue os princípios do Clean Code (Robert C. Martin): nomes que revelam a intenção, com os termos da Linguagem Ubíqua; funções pequenas, com uma única responsabilidade; e nenhuma duplicação.

### Comentários

- O código se explica pelos nomes de variáveis, funções e classes. Quando um comentário for necessário para dizer **o que** o código faz, renomeie ou extraia uma função em vez de comentar.
- Escreva comentário apenas para o que o código não consegue expressar: o **motivo** de uma escolha, o aviso de uma consequência, a referência a um requisito (RF/RNF) ou uma limitação externa (ex.: o limite de 72 bytes do bcrypt).
- Não escreva comentário que repete o código, código comentado, histórico de alterações, autoria nem marcador de seção.
- Escreva docstring apenas quando ela acrescenta informação que a assinatura não mostra.
- Ao alterar o código, atualize ou remova o comentário que deixou de ser verdadeiro.
- As regras valem também para os testes.

## Fluxo de Trabalho

### Issues e PRs

- Ao iniciar a implementação de uma issue, atribua a issue ao usuário que pediu a implementação (`gh issue edit <número> --add-assignee @me`).
- Ao abrir um PR, atribua o PR ao mesmo usuário (`gh pr create --assignee @me`) e associe a issue escrevendo `Closes #<número>` na descrição.

### Revisão da Documentação

- Ao final de toda implementação, antes de abrir o PR, revise as fontes da verdade (guia, seção 1) contra o código implementado.
- Se houver divergência, decida entre alterar a implementação ou a documentação, dando preferência a alterar a implementação. Registre a divergência, a escolha e o motivo na descrição do PR.

### Registro de Mudanças na Documentação

- Toda alteração de documentação registra o motivo na descrição do PR.
- Alterações estruturais ou arquiteturais do que está documentado (camadas, pastas, portas e adaptadores, decisões técnicas da seção 8 do guia e regras de processo) também entram em `docs/CHANGELOG.md`, com a data, o PR, o que mudou e o motivo.
- Mudanças de regra de negócio, de requisito ou de redação não entram no `docs/CHANGELOG.md`; o motivo delas fica no PR.
