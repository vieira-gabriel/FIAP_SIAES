# Changelog da Documentação

Registro das alterações estruturais e arquiteturais da documentação: camadas, pastas, portas e adaptadores, decisões técnicas (guia, seção 8) e regras de processo. Mudanças de regra de negócio, de requisito ou de redação não entram aqui; o motivo delas fica na descrição do PR (`AGENTS.md`, seção "Fluxo de Trabalho").

Cada entrada traz a data, o PR, o que mudou e o motivo. As entradas mais recentes ficam no topo.

## 2026-10-27 — PR da issue #83 (componentes de veículos)

**O que mudou:** no diagrama de componentes do C4 (`docs/ddd/c4-model.md`, seção 4), as rotas de veículos saíram de `routers/clientes.py` para o componente próprio `routers/veiculos.py`, e as portas `ClienteRepository` e `VeiculoRepository` e os adaptadores `PostgresClienteRepository` e `PostgresVeiculoRepository` passaram a constar no diagrama. O guia ganhou a linha da porta e do adaptador de veículos (seção 2.2) e a exclusão do cliente com os veículos na lista de operações atômicas (seção 5.4).

**Motivo:** a revisão da documentação ao final da issue #83 encontrou divergência entre o C4 e o guia, que define um arquivo de rotas por recurso (seções 3 e 5.5), e entre o C4 e a própria issue, que pede `routers/veiculos.py`. A implementação segue o guia e a issue, e o C4 foi corrigido. As portas de clientes e veículos já existiam no código e faltavam no diagrama.

## 2026-10-27 — PR da issue #83 (regras de fluxo de trabalho)

**O que mudou:** criação deste changelog e da seção "Fluxo de Trabalho" no `AGENTS.md`, com três regras: atribuir a issue e o PR ao usuário e associar a issue ao PR; revisar a documentação contra o código ao final de toda implementação, com preferência por alterar a implementação quando houver divergência; e registrar o motivo de toda alteração de documentação no PR e, quando estrutural ou arquitetural, neste arquivo. O guia passou a citar este arquivo entre as fontes da verdade (seção 1).

**Motivo:** pedido do grupo para que issues e PRs tenham sempre um responsável, para que código e documentação não divirjam ao final de cada entrega e para que as mudanças estruturais da documentação tenham o motivo registrado em um único lugar.
