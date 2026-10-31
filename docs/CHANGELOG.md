# Changelog da Documentação

Registro das alterações estruturais e arquiteturais da documentação: camadas, pastas, portas e adaptadores, decisões técnicas (guia, seção 8) e regras de processo. Mudanças de regra de negócio, de requisito ou de redação não entram aqui; o motivo delas fica na descrição do PR (`AGENTS.md`, seção "Fluxo de Trabalho").

Cada entrada traz a data, o PR, o que mudou e o motivo. As entradas mais recentes ficam no topo.

## 2026-10-31 — PR da issue #102 (rejeição do orçamento pelo cliente)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Rejeição do orçamento pelo cliente (RF-26, RF-18)": `POST /acompanhamento/rejeicao`, sem JWT, e o caso de uso `RejeitarOrcamento`, que despacha o `OSCanceladaEvent` para o `EstornoReservasHandler` do cancelamento. A decisão "Repetição da transação em impasse" passou a incluir o `RejeitarOrcamento`. No C4, o `RejeitarOrcamento` entrou no diagrama de componentes.

**Motivo:** o RF-26 manda cancelar a OS rejeitada e estornar as reservas (RF-18), e o evento e o handler do estorno já existiam por causa do cancelamento do Gerente (issue #95); a rejeição só precisa da mesma identificação pública da consulta e da aprovação. O caso de uso bloqueia a OS e depois o estoque, a mesma ordem do cancelamento, e por isso recebe a repetição em impasse da issue #95.

## 2026-10-31 — PR da issue #101 (entrega do veículo)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Entrega do veículo (RF-22)": `POST /ordens-servico/{id}/entrega`, para Atendente e Gerente, e o caso de uso `EntregarVeiculo`.

**Motivo:** o RF-22 restringe a entrega à equipe de atendimento, mas não define a rota. A conferência do perfil fica na rota, como no cancelamento, porque a entidade não precisa do perfil para decidir a transição, ao contrário do início da execução e da conclusão, que dependem do mecânico atribuído.

## 2026-10-31 — PR da issue #100 (conclusão da manutenção)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Conclusão da manutenção (RF-21)": `POST /ordens-servico/{id}/conclusao` e o caso de uso `ConcluirManutencao`. O método `OrdemServico.concluir_manutencao` passou a receber o `Usuario`, em vez do id, e a regra de quem pode concluir foi reunida com a do início da execução. A assinatura foi atualizada na receita da seção 5.2 do guia, no diagrama de classes do C4 e na tabela de transições da Linguagem Ubíqua (Mecânico atribuído, Gerente).

**Motivo:** o RF-21 lista os perfis Mecânico e Gerente, mas não diz se um mecânico pode concluir a OS de outro; o RF-20 diz que só o atribuído inicia. Seguiu-se a mesma regra do início, por escolha do usuário na issue #100, o que exige o `Usuario` na entidade (perfil, estado ativo e id).

## 2026-10-30 — PR da issue #99 (início da execução com baixa das peças)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Início da execução e baixa das peças (RF-20)": `POST /ordens-servico/{id}/execucao`, o caso de uso `IniciarExecucao` e o `BaixaEstoqueHandler` na transação. A decisão "Repetição da transação em impasse" passou a incluir o `IniciarExecucao`.

**Motivo:** o RF-20 manda dar baixa nas peças reservadas no início da execução, na mesma transação da mudança de status (RNF-08), mas não define a rota nem como a permissão do mecânico atribuído é checada. A OS confere o mecânico, e a rota só filtra o perfil, como na atribuição. O `IniciarExecucao` bloqueia a OS e depois o estoque, a mesma ordem do cancelamento, e por isso pode ser a transação abortada num impasse com a alocação da reposição; a repetição da issue #95 o cobre.

## 2026-10-30 — PR da issue #98 (aprovação do orçamento pelo cliente)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Aprovação do orçamento pelo cliente (RF-26)": `POST /acompanhamento/aprovacao`, sem JWT, com origem `CLIENTE` no histórico. A identificação por número da OS e CPF/CNPJ saiu do `ConsultarOSPublica` para o caso de uso `LocalizarOSDoTitular`, que a consulta e a aprovação compartilham. O rate limiting passou a ter um contador único para todas as rotas públicas. No C4, o `LocalizarOSDoTitular` entrou no diagrama, e a aprovação deixou de ligar ao `EventDispatcher`.

**Motivo:** a aprovação e, depois dela, a rejeição (issue #102) precisam da mesma identificação da consulta e do mesmo `404` indistinto; extrair o caso de uso evita repetir a regra que protege contra a adivinhação do documento. O contador único fecha uma brecha: com um contador por rota, quem alternasse entre a consulta e a aprovação teria o dobro de tentativas por minuto, contra o limite de 10 requisições por IP da RNF-05. A aprovação não emite evento porque só muda o status; o estoque só é tocado na reserva, na reposição e no cancelamento.

## 2026-10-30 — PR da issue #97 (rate limiting das rotas públicas)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Rate limiting (RNF-05)" no lugar da linha "Rate limiting" (o `limite_publico` do SlowAPI em `presentation/middlewares/rate_limit.py`, o limite de `RATE_LIMIT_PUBLICO` lido pelo container, a contagem por IP e o que conta para o limite), e a tabela de erros da seção 5.5 passou a listar o `429` (`LIMITE_DE_REQUISICOES_EXCEDIDO`, com `Retry-After`). A linha "Consulta pública da OS" deixou de dizer que a rota não tinha limite.

**Motivo:** a RNF-05 manda limitar as rotas públicas, mas não define onde o limite é lido, o que conta para ele nem o formato do estouro. O `429` não constava na tabela do guia, e o card da issue pedia a atualização. O corpo fora do DTO não conta porque o FastAPI o recusa antes da rota, e ele não consulta nenhum dado; o limite não confia em `X-Forwarded-For` porque a instância única do MVP não fica atrás de proxy, e confiar no cabeçalho deixaria o cliente escolher o próprio IP.

## 2026-10-30 — PR da issue #96 (consulta pública da OS)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Consulta pública da OS (RF-25)": `POST /acompanhamento`, sem JWT, com o número e o documento no corpo, a mesma resposta `404` para número inexistente, número ou documento malformado e documento de outro titular, e uma resposta sem dados do cliente. No C4, o caso de uso `ConsultarStatusPublico` passou a se chamar `ConsultarOSPublica`.

**Motivo:** o RF-25 pede a consulta pública sem indicar qual dos dois dados está errado, mas não define a forma da requisição. O documento vai no corpo, e não na URL, para não aparecer nos logs de acesso. A validação do formato fica no caso de uso porque o DTO responderia `400` a um documento malformado, o que diferenciaria esse caso do número inexistente. O nome do caso de uso passou a descrever o que ele faz: consulta a OS inteira, e não só o status. O rate limiting da rota (RNF-05) continua na issue #97.

## 2026-10-30 — PR da issue #95 (cancelamento pelo Gerente)

**O que mudou:** a seção 8.1 do guia ganhou as decisões "Cancelamento pelo Gerente (RF-23, RF-18)" (`POST /ordens-servico/{id}/cancelamento`, `CancelarOS` e `EstornoReservasHandler` na transação), "Higienização do motivo contra XSS (RNF-04)" (o motivo com `<` responde `400`) e "Repetição da transação em impasse (RF-19, RF-23)". A decisão em aberto "Ordem dos bloqueios entre alocação e cancelamento" saiu da seção 8.2, e as linhas do guia que a citavam (reserva, alocação, persistência da OS e ponto de montagem) passaram a apontar para a nova decisão. No C4, o handler de estorno passou a se chamar `EstornoReservasHandler` e o caso de uso `CancelarOS` entrou no diagrama.

**Motivo:** a alocação da reposição (issue #94) bloqueia o estoque e depois a OS, e o cancelamento bloqueia a OS e depois o estoque; com as duas se cruzando, o PostgreSQL aborta uma transação. O grupo escolheu, entre as opções A, B e C da seção 8.2, repetir a transação, que mantém a ordem dos bloqueios e a prioridade pela OS mais antiga (RF-19). Para a higienização do motivo, foi escolhida a recusa do texto com `<`, que preserva o texto original no histórico (RF-24), em vez de escapá-lo. O nome `EstornoReservasHandler` substitui o `EstornoPecasHandler` do C4 por descrever o que o handler faz: devolver reservas, e não peças.

## 2026-10-30 — PR da issue #94 (alocação das peças repostas)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Alocação das peças repostas (RF-19)": o `AlocacaoPecasPendentesHandler` trata o `SaldoPecaAtualizadoEvent` (reposição e ajuste para cima) na transação da operação, aloca o saldo atual às OS pendentes da mais antiga para a mais nova e libera as OS de `AGUARDANDO_PECA` que ficam sem pendência. O `ReservaPecasHandler` passou a delegar a repartição do saldo ao mesmo `alocar_saldo`, e a lista de handlers do `container.py` ganhou o novo handler.

**Motivo:** o RF-19 manda alocar o saldo às OS pendentes quando ele aumenta, na mesma transação (RNF-08). A reserva da conclusão do orçamento (RF-18) e a alocação da reposição repartem o saldo do mesmo jeito, então o núcleo fica em um lugar só. O handler usa o saldo atual do estoque, e não o do evento, porque duas operações na mesma transação geram dois eventos e o primeiro chega com um saldo antigo. A releitura de cada OS depois do estoque segue a ordem descrita na decisão em aberto "Ordem dos bloqueios entre alocação e cancelamento" (seção 8.2), que continua em aberto.

## 2026-10-30 — PR da issue #93 (reserva de peças)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Reserva das peças na conclusão do orçamento (RF-18)": o `ReservaPecasHandler` trata o `OrcamentoFinalizadoEvent` na transação da conclusão, aloca o saldo pela OS mais antiga e aplica cada alocação com `OrdemServico.alocar_peca`. A lista `app.state.fabricas_de_handlers`, que nascia vazia, passou a trazer esse handler, registrado em `_fabricas_de_handlers` no `container.py`.

**Motivo:** o RF-18 manda reservar as peças na conclusão do orçamento e deixar o resto pendente, e o RF-19 manda dar a prioridade à OS mais antiga. O handler reaproveita o `alocar_pendencias` da #43, para a OS nova só usar o que sobra depois das OS que já esperam a mesma peça, e roda na transação da conclusão (RNF-08), com os estoques já bloqueados pelo `FinalizarOrcamento` (RNF-09). A releitura de uma OS mais antiga, quando ela recebe saldo, herda o impasse registrado na decisão em aberto "Ordem dos bloqueios entre alocação e cancelamento" (seção 8.2).

## 2026-10-30 — PR da issue #92 (itens e conclusão do orçamento)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Itens e conclusão do orçamento (RF-17)": rotas para incluir e remover serviços e peças da OS e para concluir o orçamento, com os códigos de resposta de cada caso. O `FinalizarOrcamento` passou a receber o `EventDispatcher` e a despachar o `OrcamentoFinalizadoEvent` depois de salvar a OS, na mesma unidade de trabalho.

**Motivo:** o RF-17 define as regras dos itens e do congelamento, mas não a forma das rotas. O despacho dentro da transação é o que permite à reserva das peças (RF-18, issue #93) gravar junto com a conclusão e desfazer tudo se falhar, como pede o RF-17 (RNF-08). A decisão de deixar qualquer Mecânico ou Gerente alterar os itens, e não só o mecânico atribuído, segue o texto do RF-17, que lista só os perfis.

## 2026-10-30 — PR da issue #91 (atribuição do mecânico)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Atribuição do mecânico (RF-16)": `POST /ordens-servico/{id}/mecanico` para Mecânico e Gerente, com o `mecanico_id` opcional no corpo (o Mecânico omite, o Gerente informa). `OrdemServico.atribuir_mecanico` passou a receber o mecânico e o responsável como `Usuario`, como o `iniciar_execucao`, e concentra as regras de quem pode atribuir. O diagrama de classes e a descrição das transições do C4 acompanham a nova assinatura.

**Motivo:** a tabela de transições da Linguagem Ubíqua diz que o histórico grava o usuário que executa a transição, mas o `atribuir_mecanico(mecanico_id)` gravava o mecânico atribuído, e o histórico não mostraria o Gerente que atribuiu a OS a outro (RF-24). Receber os dois usuários também permite recusar, no domínio, o mecânico que atribui a OS a outro e o indicado que não é um mecânico ativo. As duas escolhas (histórico com o responsável e só mecânico ativo como indicado) foram decididas com o usuário ao implementar a issue.

## 2026-10-30 — PR #142 (listagem de OS)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Listagem de OS (RF-14)": `GET /ordens-servico` para os três perfis, com os filtros combináveis `documento`, `placa`, `status`, `mecanico_id` e período de abertura, resposta da mais recente para a mais antiga e sem paginação. A porta `VeiculoRepository` ganhou `listar_por_placa`, que devolve também os veículos excluídos.

**Motivo:** o RF-14 não define a forma dos filtros nem da resposta. A busca por placa precisa incluir os veículos excluídos, porque as OS deles continuam no histórico (RF-09); com a busca só de veículos ativos, a listagem esconderia as OS de um veículo excluído e, com a placa reaproveitada, as do veículo antigo.

## 2026-10-30 — PR #141 (detalhamento da OS)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Detalhamento da OS (RF-15)": `GET /ordens-servico/{id}` para os três perfis, com cliente e veículo (mesmo excluídos), itens com as quantidades reservada e pendente, orçamento, histórico e a estimativa de entrega calculada na consulta. A seção 8.2 ganhou a decisão em aberto "Prazo de reposição sem limite máximo".

**Motivo:** o RF-15 pede todos os dados da OS numa consulta, mas não define a forma da resposta. O detalhamento é a primeira rota de leitura da OS e mostrou que um prazo de reposição acima de cerca de 2,9 milhões de dias, aceito hoje no cadastro de peças, impede a estimativa e deixa a OS ilegível; a escolha entre limitar o cadastro e tolerar o estouro na consulta é do grupo.

## 2026-10-30 — PR #140 (despacho dos eventos na transação)

**O que mudou:** a seção 8.1 do guia ganhou a decisão "Despacho dos eventos na transação (RNF-08)": cada requisição monta o `EventDispatcher` com os handlers criados sobre a sessão da unidade de trabalho, e os handlers entram em `app.state.fabricas_de_handlers`, uma lista de pares `(tipo_do_evento, fabrica)`. A linha "Ponto de entrada e montagem" deixou de dizer que os handlers são registrados direto em `_eventos_da_requisicao`.

**Motivo:** a issue #89 liga o `EventDispatcher` à unidade de trabalho para que a reação a um evento grave na mesma transação da operação e uma falha desfaça as duas. Os requisitos não definem como os handlers são registrados; a lista em `app.state` mantém o registro em um só lugar e permite trocá-la nos testes, em vez de editar o container a cada handler da Fase 5.

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
