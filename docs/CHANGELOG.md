# Changelog da Documentação

Registro das alterações estruturais e arquiteturais da documentação: camadas, pastas, portas e adaptadores, decisões técnicas (guia, seção 8) e regras de processo. Mudanças de regra de negócio, de requisito ou de redação não entram aqui; o motivo delas fica na descrição do PR (`AGENTS.md`, seção "Fluxo de Trabalho").

Cada entrada traz a data, o PR, o que mudou e o motivo. As entradas mais recentes ficam no topo.

## 2026-10-30 — PR #139 (abertura da OS)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Abertura da OS (RF-13)": `POST /ordens-servico`, para Atendente e Gerente, com o documento e a placa no corpo e os objetos opcionais `cliente` e `veiculo`, usados só para cadastrar o que ainda não existe; sem eles, um cliente ou veículo inexistente responde `404`, e a placa de um veículo de outro cliente responde `422` (`OSDeOutroCliente`). O número é refeito com outro UUID até 5 vezes quando já existe (`NumeroOSIndisponivel`). Cliente, veículo e OS são gravados na mesma unidade de trabalho. Em `docs/estrutura-de-pastas.md`, o caso de uso `criar_os.py` deixou de constar como pendente.

**Motivo:** os requisitos RF-04, RF-07 e RF-13 pedem o cadastro de cliente e veículo no mesmo fluxo da abertura, mas não definem a forma do corpo da requisição. A escolha de objetos opcionais fica restrita ao schema e ao router, e vale para os próximos casos de uso da Fase 5.

## 2026-10-29 — PR da issue #88 (persistência da OS)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Persistência da OS" (quatro tabelas com os modelos em `infrastructure/database/ordem_servico_model.py`, número único com `NumeroOSJaCadastrado`, chaves estrangeiras, orçamento gravado como os dois subtotais, CHECKs nas quantidades de `itens_peca`, triggers que recusam UPDATE, DELETE e TRUNCATE no histórico, ordem dos itens e do histórico, bloqueio `SELECT ... FOR UPDATE` nas buscas de uma OS, lista de pendências sem bloqueio e ordem dos bloqueios entre OS e estoque) e a linha de Migrations passou a citar a `0007` e o teste do trigger. O item "Item excluído do catálogo antes do congelamento" saiu da seção 8.2 para a 8.1. Em `docs/estrutura-de-pastas.md` e na Linguagem Ubíqua, o adaptador da OS deixou de constar como provisório.

**Motivo:** a issue #88 cria a persistência da OS, da qual dependem todos os cards da Fase 5, e as escolhas técnicas dela (bloqueio, trigger, ordenação, colisão do número) passam a valer para os casos de uso da Fase 5. A lista de pendências ficou sem bloqueio depois que a revisão da implementação apontou o impasse entre a exclusão de peça (estoque e depois OS) e o cancelamento com estorno (OS e depois estoque). O mesmo impasse entre a alocação da reposição e o cancelamento ficou registrado na seção 8.2, com as opções e os custos, para o grupo decidir nas issues #94 e #95. A recusa do item excluído foi decidida com o usuário ao implementar a conferência pedida no comentário da issue, que impede a OS de ficar pendente de uma peça excluída durante a conclusão do orçamento.

## 2026-10-29 — PR #128 (estado das Fases 0 a 3)

**O que mudou:** no guia, a nova seção 4.4 define a construção de entidades (argumentos nomeados; o construtor só reconstitui, e a criação com efeito colateral vem de uma fábrica, como `OrdemServico.abrir`); a seção 7 passou a dizer que a `main` **deve ser** protegida, com a configuração pendente com o dono do repositório; a seção 8.1 lista as migrations `0002` a `0006`; e a seção 8.2 recebeu sete decisões em aberto (OS sem itens, item excluído do catálogo, exceção da quantidade de peça, token de usuário desativado ou rebaixado, perfil Gerente no cadastro de usuários, reativação de cliente e caractere NUL nos textos). Em `docs/estrutura-de-pastas.md`, a seção 6 foi atualizada para o que já existe (portas, adaptadores, migrations e relatórios de `docs/security/`) e para o que falta (tabela e adaptador da OS, caso de uso `criar_os.py`, eventos e handlers).

**Motivo:** a documentação descrevia a `main` de antes dos cadastros de clientes, veículos, serviços e peças, das portas de repositório e dos relatórios de segurança, e o guia afirmava uma proteção da `main` que a API do GitHub não confirma (`protected: false`). As decisões em aberto foram levantadas nas revisões dos PRs #123 a #132 e, conforme o `AGENTS.md`, ficam registradas no guia até o grupo decidir, em vez de serem escolhidas por quem implementa.

## 2026-10-27 — PR da issue #83 (componentes de veículos)

**O que mudou:** no diagrama de componentes do C4 (`docs/ddd/c4-model.md`, seção 4), as rotas de veículos saíram de `routers/clientes.py` para o componente próprio `routers/veiculos.py`, e as portas `ClienteRepository` e `VeiculoRepository` e os adaptadores `PostgresClienteRepository` e `PostgresVeiculoRepository` passaram a constar no diagrama. O guia ganhou a linha da porta e do adaptador de veículos (seção 2.2) e a exclusão do cliente com os veículos na lista de operações atômicas (seção 5.4).

**Motivo:** a revisão da documentação ao final da issue #83 encontrou divergência entre o C4 e o guia, que define um arquivo de rotas por recurso (seções 3 e 5.5), e entre o C4 e a própria issue, que pede `routers/veiculos.py`. A implementação segue o guia e a issue, e o C4 foi corrigido. As portas de clientes e veículos já existiam no código e faltavam no diagrama.

## 2026-10-27 — PR da issue #83 (regras de fluxo de trabalho)

**O que mudou:** criação deste changelog e da seção "Fluxo de Trabalho" no `AGENTS.md`, com três regras: atribuir a issue e o PR ao usuário e associar a issue ao PR; revisar a documentação contra o código ao final de toda implementação, com preferência por alterar a implementação quando houver divergência; e registrar o motivo de toda alteração de documentação no PR e, quando estrutural ou arquitetural, neste arquivo. O guia passou a citar este arquivo entre as fontes da verdade (seção 1).

**Motivo:** pedido do grupo para que issues e PRs tenham sempre um responsável, para que código e documentação não divirjam ao final de cada entrega e para que as mudanças estruturais da documentação tenham o motivo registrado em um único lugar.
