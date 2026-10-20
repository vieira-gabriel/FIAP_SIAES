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
