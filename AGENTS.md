# Instruções para Assistentes de IA

Antes de criar ou alterar qualquer arquivo neste repositório, leia `docs/guia-de-desenvolvimento.md`. Ele define onde cada parte do código fica, a regra de dependência entre camadas e as convenções do projeto. A seção 9 do guia contém as regras específicas para assistentes de IA.

## Princípios de Desenvolvimento

Adaptados das diretrizes de [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills/blob/main/CLAUDE.md). Elas trocam velocidade por cuidado; em tarefas triviais, aplique-as com bom senso.

### Pensar antes de codificar

- Declare as premissas antes de implementar. Se não tiver certeza, pergunte.
- Quando o pedido admitir mais de uma interpretação, apresente as interpretações em vez de escolher uma sem avisar.
- Se existir um caminho mais simples que o pedido, diga, com o ganho e o custo de cada caminho.
- Se algo não estiver claro, pare, diga o que não está claro e pergunte.

### Simplicidade primeiro

- Escreva o mínimo de código que resolve o problema pedido.
- Não acrescente funcionalidade, configuração ou flexibilidade que ninguém pediu.
- Não crie abstração para um único uso.
- Não trate cenários que não podem ocorrer.
- Se a solução ficou muito maior do que o problema exige, reescreva-a menor.

### Mudanças cirúrgicas

- Altere só o que a tarefa exige; cada linha alterada deve ser rastreável até o pedido.
- Não melhore, refatore nem reformate código, comentário ou formatação vizinhos que não fazem parte da tarefa.
- Siga o estilo do código existente, mesmo que você escrevesse de outro jeito.
- Remova apenas os imports, variáveis e funções que a sua mudança deixou sem uso. Código morto que já existia é informado ao usuário, e não removido.

### Execução orientada a metas

- Transforme cada tarefa em um critério verificável. Exemplos: "corrigir o bug" vira "escrever um teste que reproduz o bug e fazê-lo passar"; "validar a entrada" vira "escrever testes para as entradas inválidas e fazê-los passar".
- Em tarefas com várias etapas, escreva um plano curto em que cada etapa tem a sua verificação.
- Só considere a tarefa concluída depois que a verificação passar.

## Clean Code

Toda implementação segue os princípios do Clean Code (Robert C. Martin): nomes que revelam a intenção, com os termos da Linguagem Ubíqua; funções pequenas, com uma única responsabilidade; e nenhuma duplicação.

### Comentários

- O código se explica pelos nomes de variáveis, funções e classes. Quando um comentário for necessário para dizer **o que** o código faz, renomeie ou extraia uma função em vez de comentar.
- Escreva comentário apenas para o que o código não consegue expressar: o **motivo** de uma escolha, o aviso de uma consequência, a referência a um requisito (RF/RNF) ou uma limitação externa (ex.: o limite de 72 bytes do bcrypt).
- Não escreva comentário que repete o código, código comentado, histórico de alterações, autoria nem marcador de seção.
- Escreva docstring apenas quando ela acrescenta informação que a assinatura não mostra.
- Ao alterar o código, atualize ou remova o comentário que deixou de ser verdadeiro.
- As regras valem também para os testes.
