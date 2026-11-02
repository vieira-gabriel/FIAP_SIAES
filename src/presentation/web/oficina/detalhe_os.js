// Detalhe da OS com as ações do fluxo (RF-15 a RF-24).
//
// Cada botão só aparece no status em que a transição vale e para o perfil que a rota aceita;
// a OS e a API continuam sendo quem recusa uma ação fora de hora.

import { chamarApi } from "/comum/api.js";
import {
  NOMES_DOS_STATUS,
  aviso,
  campo,
  campoDeSelecao,
  dataHora,
  el,
  executarComAviso,
  lerFormulario,
  moeda,
  selo,
  trocarConteudo,
} from "/comum/dom.js";
import { ATENDIMENTO, GERENTE, OFICINA, pode } from "/oficina/perfis.js";
import { nomeDoMecanicoPorOS } from "/oficina/quadro.js";

const CANCELAVEIS = ["RECEBIDA", "EM_DIAGNOSTICO", "AGUARDANDO_APROVACAO", "AGUARDANDO_PECA", "AGUARDANDO_EXECUCAO", "EM_EXECUCAO"];
const ORIGENS = { USUARIO: "Funcionário", CLIENTE: "Cliente", SISTEMA: "Sistema" };

export async function mostrarDetalheDaOS(alvo, sessao, id, mensagem) {
  const os = await chamarApi("GET", `/ordens-servico/${id}`);
  await conhecerNomeDoMecanico(os, sessao);
  const areaDoAviso = el("div", {}, mensagem);
  const recarregar = (texto) => mostrarDetalheDaOS(alvo, sessao, id, texto && aviso(texto, "sucesso"));
  const contexto = { os, sessao, areaDoAviso, recarregar };

  trocarConteudo(
    alvo,
    el(
      "div",
      { classe: "barra" },
      el("a", { href: "#/quadro", classe: "botao discreto" }, "← Quadro"),
      el("h1", {}, `OS ${os.numero}`),
      selo(os.status),
    ),
    areaDoAviso,
    await painelDeAcoes(contexto),
    el(
      "div",
      { classe: "grade-2" },
      cartaoDosDados(os, sessao),
      cartaoDoOrcamento(os),
    ),
    cartaoDosItens(contexto),
    cartaoDoHistorico(os, sessao),
  );
}

// Só o Gerente lista os usuários; os outros perfis veem o nome que veio do quadro.
async function conhecerNomeDoMecanico(os, sessao) {
  if (!os.mecanico_id || nomeDoMecanicoPorOS.get(os.id) || !pode(sessao, GERENTE)) return;
  const usuarios = await chamarApi("GET", "/usuarios");
  nomeDoMecanicoPorOS.set(os.id, usuarios.find((u) => u.id === os.mecanico_id)?.nome);
}

function nomeDoMecanico(os, sessao) {
  if (!os.mecanico_id) return "Não atribuído";
  if (os.mecanico_id === sessao.usuarioId) return "Você";
  return nomeDoMecanicoPorOS.get(os.id) ?? "Atribuído";
}

function cartaoDosDados(os, sessao) {
  return el(
    "section",
    { classe: "cartao" },
    el("h2", {}, "Atendimento"),
    el(
      "dl",
      { classe: "dados" },
      el("dt", {}, "Cliente"),
      el("dd", {}, os.cliente.nome),
      el("dt", {}, "Veículo"),
      el("dd", {}, `${os.veiculo.placa} · ${os.veiculo.marca} ${os.veiculo.modelo}`),
      el("dt", {}, "Mecânico"),
      el("dd", {}, nomeDoMecanico(os, sessao)),
      el("dt", {}, "Abertura"),
      el("dd", {}, dataHora(os.data_abertura)),
      el("dt", {}, "Início da execução"),
      el("dd", {}, dataHora(os.data_inicio_execucao)),
      el("dt", {}, "Finalização"),
      el("dd", {}, dataHora(os.data_finalizacao)),
      el("dt", {}, "Previsão de entrega"),
      el("dd", {}, dataHora(os.estimativa_entrega)),
    ),
  );
}

function cartaoDoOrcamento(os) {
  const linkDoCliente = `${location.origin}/cliente/#numero=${encodeURIComponent(os.numero)}`;
  return el(
    "section",
    { classe: "cartao" },
    el("h2", {}, "Orçamento"),
    os.orcamento
      ? el(
          "dl",
          { classe: "dados" },
          el("dt", {}, "Serviços"),
          el("dd", {}, moeda(os.orcamento.subtotal_servicos)),
          el("dt", {}, "Peças"),
          el("dd", {}, moeda(os.orcamento.subtotal_pecas)),
          el("dt", {}, "Total"),
          el("dd", { classe: "destaque-grande" }, moeda(os.orcamento.total)),
        )
      : el("p", { classe: "suave" }, "Ainda não concluído. Os valores são congelados na conclusão."),
    el("h3", {}, "Link de acompanhamento do cliente"),
    el("p", { classe: "suave" }, "O cliente informa o CPF/CNPJ para ver a OS."),
    el(
      "div",
      { classe: "acoes" },
      el("input", { value: linkDoCliente, readonly: true, "aria-label": "Link do cliente" }),
      el(
        "button",
        {
          onclick: async (evento) => {
            await navigator.clipboard?.writeText(linkDoCliente).catch(() => {});
            evento.target.textContent = "Copiado";
          },
        },
        "Copiar",
      ),
    ),
  );
}

async function executarAcao(contexto, operacao, sucesso) {
  const { ok } = await executarComAviso(contexto.areaDoAviso, operacao);
  if (ok) await contexto.recarregar(sucesso);
}

function botaoDeAcao(contexto, texto, caminho, sucesso, { classe = "primario", corpo, pergunta } = {}) {
  return el(
    "button",
    {
      classe,
      onclick: async (evento) => {
        if (pergunta && !confirm(pergunta)) return;
        evento.target.disabled = true;
        await executarAcao(contexto, () => chamarApi("POST", `/ordens-servico/${contexto.os.id}/${caminho}`, corpo), sucesso);
        evento.target.disabled = false;
      },
    },
    texto,
  );
}

async function painelDeAcoes(contexto) {
  const { os, sessao } = contexto;
  const acoes = [];
  const oficina = pode(sessao, OFICINA);
  const atendimento = pode(sessao, ATENDIMENTO);

  if (os.status === "RECEBIDA") {
    if (sessao.perfil === "MECANICO") acoes.push(botaoDeAcao(contexto, "Assumir esta OS", "mecanico", "OS assumida. Diagnóstico iniciado."));
    if (sessao.perfil === "GERENTE") acoes.push(await formularioDeAtribuicao(contexto));
  }
  if (os.status === "EM_DIAGNOSTICO" && oficina) {
    acoes.push(
      botaoDeAcao(contexto, "Concluir orçamento", "orcamento", "Orçamento concluído e enviado ao cliente.", {
        pergunta: "Concluir o orçamento? Os valores são congelados e os itens deixam de mudar.",
      }),
    );
  }
  if (os.status === "AGUARDANDO_APROVACAO" && atendimento) {
    acoes.push(
      botaoDeAcao(contexto, "Cliente aprovou no balcão", "orcamento/aprovacao", "Aprovação registrada.", {
        pergunta: `Registrar que o cliente aprovou o orçamento de ${moeda(os.orcamento?.total)}?`,
      }),
      botaoDeAcao(contexto, "Cliente rejeitou no balcão", "orcamento/rejeicao", "Rejeição registrada. A OS foi cancelada.", {
        classe: "perigo",
        pergunta: "Registrar que o cliente rejeitou o orçamento? A OS será cancelada e as peças voltam ao estoque.",
      }),
    );
  }
  if (os.status === "AGUARDANDO_PECA") {
    acoes.push(el("p", { classe: "aviso aviso-info" }, "A OS sai daqui sozinha quando as peças pendentes forem repostas no estoque."));
  }
  if (os.status === "AGUARDANDO_EXECUCAO" && oficina) {
    acoes.push(botaoDeAcao(contexto, "Iniciar execução", "execucao", "Execução iniciada. As peças receberam baixa no estoque."));
  }
  if (os.status === "EM_EXECUCAO" && oficina) {
    acoes.push(botaoDeAcao(contexto, "Concluir manutenção", "conclusao", "Manutenção concluída."));
  }
  if (os.status === "FINALIZADA" && atendimento) {
    acoes.push(
      botaoDeAcao(contexto, "Entregar veículo", "entrega", "Veículo entregue.", {
        pergunta: "Confirmar a entrega do veículo ao cliente?",
      }),
    );
  }
  if (CANCELAVEIS.includes(os.status) && pode(sessao, GERENTE)) {
    acoes.push(formularioDeCancelamento(contexto));
  }

  if (!acoes.length) return null;
  return el("section", { classe: "cartao" }, el("h2", {}, "Próximo passo"), el("div", { classe: "acoes" }, acoes));
}

async function formularioDeAtribuicao(contexto) {
  const usuarios = await chamarApi("GET", "/usuarios");
  const mecanicos = usuarios.filter((u) => u.perfil === "MECANICO" && u.ativo);
  if (!mecanicos.length) return el("p", { classe: "aviso aviso-info" }, "Nenhum mecânico ativo cadastrado.");
  const formulario = el(
    "form",
    {
      classe: "linha",
      onsubmit: async (evento) => {
        evento.preventDefault();
        await executarAcao(
          contexto,
          () => chamarApi("POST", `/ordens-servico/${contexto.os.id}/mecanico`, lerFormulario(formulario)),
          "Mecânico atribuído. Diagnóstico iniciado.",
        );
      },
    },
    campoDeSelecao("Mecânico", "mecanico_id", mecanicos.map((m) => [m.id, m.nome])),
    el("button", { type: "submit", classe: "primario" }, "Atribuir"),
  );
  return formulario;
}

function formularioDeCancelamento(contexto) {
  const formulario = el(
    "form",
    {
      classe: "linha",
      onsubmit: async (evento) => {
        evento.preventDefault();
        if (!confirm("Cancelar esta OS? A ação não pode ser desfeita.")) return;
        await executarAcao(
          contexto,
          () => chamarApi("POST", `/ordens-servico/${contexto.os.id}/cancelamento`, lerFormulario(formulario)),
          "OS cancelada.",
        );
      },
    },
    campo("Motivo do cancelamento", { name: "motivo", required: true, maxlength: 500 }),
    el("button", { type: "submit", classe: "perigo" }, "Cancelar OS"),
  );
  return el("details", {}, el("summary", {}, "Cancelar OS"), formulario);
}

function cartaoDosItens(contexto) {
  const { os, sessao } = contexto;
  const editavel = os.status === "EM_DIAGNOSTICO" && pode(sessao, OFICINA);
  const remover = (tipo, itemId, nome) =>
    el(
      "button",
      {
        classe: "discreto perigo",
        "aria-label": `Remover ${nome}`,
        onclick: () =>
          executarAcao(contexto, () => chamarApi("DELETE", `/ordens-servico/${os.id}/${tipo}/${itemId}`), `${nome} removido.`),
      },
      "Remover",
    );

  return el(
    "section",
    { classe: "cartao" },
    el("h2", {}, "Serviços"),
    os.servicos.length
      ? el(
          "div",
          { classe: "tabela-rolavel" },
          el(
            "table",
            {},
            el("thead", {}, el("tr", {}, el("th", {}, "Serviço"), el("th", { classe: "numero" }, "Tempo"), el("th", { classe: "numero" }, "Preço"), editavel && el("th", {}))),
            el(
              "tbody",
              {},
              os.servicos.map((s) =>
                el(
                  "tr",
                  {},
                  el("td", {}, s.nome),
                  el("td", { classe: "numero" }, `${s.tempo_estimado_minutos} min`),
                  el("td", { classe: "numero" }, moeda(s.preco_congelado)),
                  editavel && el("td", {}, remover("servicos", s.servico_id, s.nome)),
                ),
              ),
            ),
          ),
        )
      : el("p", { classe: "suave" }, "Nenhum serviço."),
    editavel && formularioDeServico(contexto),
    el("h2", {}, "Peças"),
    os.pecas.length
      ? el(
          "div",
          { classe: "tabela-rolavel" },
          el(
            "table",
            {},
            el(
              "thead",
              {},
              el(
                "tr",
                {},
                el("th", {}, "Peça"),
                el("th", { classe: "numero" }, "Qtd."),
                el("th", { classe: "numero" }, "Reservada"),
                el("th", { classe: "numero" }, "Pendente"),
                el("th", { classe: "numero" }, "Preço unit."),
                editavel && el("th", {}),
              ),
            ),
            el(
              "tbody",
              {},
              os.pecas.map((p) =>
                el(
                  "tr",
                  {},
                  el("td", {}, p.nome),
                  el("td", { classe: "numero" }, p.quantidade),
                  el("td", { classe: "numero" }, p.quantidade_reservada),
                  el("td", { classe: "numero" }, p.quantidade_pendente),
                  el("td", { classe: "numero" }, moeda(p.preco_unitario_congelado)),
                  editavel && el("td", {}, remover("pecas", p.peca_id, p.nome)),
                ),
              ),
            ),
          ),
        )
      : el("p", { classe: "suave" }, "Nenhuma peça."),
    editavel && formularioDePeca(contexto),
  );
}

function formularioDeServico(contexto) {
  const formulario = el(
    "form",
    {
      classe: "linha",
      onsubmit: async (evento) => {
        evento.preventDefault();
        await executarAcao(
          contexto,
          () => chamarApi("POST", `/ordens-servico/${contexto.os.id}/servicos`, lerFormulario(formulario)),
          "Serviço incluído.",
        );
      },
    },
  );
  chamarApi("GET", "/servicos").then((servicos) => {
    const disponiveis = servicos.filter((s) => !contexto.os.servicos.some((i) => i.servico_id === s.id));
    trocarConteudo(
      formulario,
      disponiveis.length
        ? [
            campoDeSelecao("Incluir serviço", "servico_id", disponiveis.map((s) => [s.id, `${s.nome} · ${moeda(s.valor_base)}`])),
            el("button", { type: "submit" }, "Incluir"),
          ]
        : el("p", { classe: "suave" }, "Todos os serviços do catálogo já estão na OS."),
    );
  });
  return formulario;
}

function formularioDePeca(contexto) {
  const formulario = el(
    "form",
    {
      classe: "linha",
      onsubmit: async (evento) => {
        evento.preventDefault();
        const dados = lerFormulario(formulario);
        await executarAcao(
          contexto,
          () =>
            chamarApi("POST", `/ordens-servico/${contexto.os.id}/pecas`, {
              peca_id: dados.peca_id,
              quantidade: Number(dados.quantidade),
            }),
          "Peça incluída.",
        );
      },
    },
  );
  chamarApi("GET", "/pecas").then((pecas) => {
    const disponiveis = pecas.filter((p) => !contexto.os.pecas.some((i) => i.peca_id === p.id));
    trocarConteudo(
      formulario,
      disponiveis.length
        ? [
            campoDeSelecao(
              "Incluir peça",
              "peca_id",
              disponiveis.map((p) => [p.id, `${p.nome} · ${moeda(p.preco_unitario)} · saldo ${p.saldo_disponivel}`]),
            ),
            campo("Quantidade", { name: "quantidade", type: "number", min: 1, step: 1, value: 1, required: true }),
            el("button", { type: "submit" }, "Incluir"),
          ]
        : el("p", { classe: "suave" }, "Todas as peças do catálogo já estão na OS."),
    );
  });
  return formulario;
}

function cartaoDoHistorico(os, sessao) {
  return el(
    "section",
    { classe: "cartao" },
    el("h2", {}, "Histórico de status"),
    el(
      "ol",
      { classe: "linha-do-tempo" },
      [...os.historico].reverse().map((r) =>
        el(
          "li",
          {},
          el("strong", {}, r.status_anterior ? `${NOMES_DOS_STATUS[r.status_anterior]} → ${NOMES_DOS_STATUS[r.status_novo]}` : `Aberta como ${NOMES_DOS_STATUS[r.status_novo]}`),
          el("br"),
          el(
            "small",
            { classe: "suave" },
            `${dataHora(r.data_hora)} · ${ORIGENS[r.origem] ?? r.origem}${r.usuario_id === sessao.usuarioId ? " (você)" : ""}`,
          ),
          r.motivo && el("div", {}, `Motivo: ${r.motivo}`),
        ),
      ),
    ),
  );
}
