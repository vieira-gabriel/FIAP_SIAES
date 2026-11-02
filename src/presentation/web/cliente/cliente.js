// Frente do Cliente: consulta da OS e decisão sobre o orçamento, sem login (RF-25, RF-26).
//
// O número da OS pode vir no link depois do "#" (/cliente/#numero=529-7F3A9C2B): o fragmento
// não é enviado ao servidor e não fica nos logs de acesso. O documento nunca vai para a URL.

import { chamarApi } from "/comum/api.js";
import { aviso, campo, dataHora, el, lerFormulario, moeda, selo, trocarConteudo } from "/comum/dom.js";

const conteudo = document.getElementById("conteudo");

const EXPLICACOES = {
  RECEBIDA: "Recebemos o seu veículo e ele aguarda um mecânico.",
  EM_DIAGNOSTICO: "O mecânico está avaliando o veículo e montando o orçamento.",
  AGUARDANDO_APROVACAO: "O orçamento está pronto e aguarda a sua decisão.",
  AGUARDANDO_PECA: "Orçamento aprovado. Estamos aguardando a chegada de peças.",
  AGUARDANDO_EXECUCAO: "Orçamento aprovado e peças separadas. O serviço começa em breve.",
  EM_EXECUCAO: "O serviço está sendo executado.",
  FINALIZADA: "O serviço terminou. O veículo está pronto para retirada.",
  ENTREGUE: "O veículo já foi entregue.",
  CANCELADA: "Esta ordem de serviço foi cancelada.",
};

function numeroDoLink() {
  return new URLSearchParams(location.hash.slice(1)).get("numero") ?? "";
}

function mensagemDoErro(erro) {
  if (erro.status === 429) {
    const espera = erro.retryAfter ? ` Tente de novo em ${erro.retryAfter} segundos.` : "";
    return `Muitas consultas seguidas deste endereço.${espera}`;
  }
  if (erro.status === 404) return "Não encontramos uma OS com esse número e esse CPF/CNPJ.";
  return erro.message;
}

function mostrarFormulario(numeroInicial = numeroDoLink()) {
  const areaDoAviso = el("div");
  const formulario = el(
    "form",
    {
      onsubmit: async (evento) => {
        evento.preventDefault();
        const botao = formulario.querySelector("button");
        botao.disabled = true;
        const consulta = lerFormulario(formulario);
        try {
          mostrarAcompanhamento(await chamarApi("POST", "/acompanhamento", consulta), consulta);
        } catch (erro) {
          trocarConteudo(areaDoAviso, aviso(mensagemDoErro(erro)));
          botao.disabled = false;
        }
      },
    },
    campo("Número da OS", {
      name: "numero",
      required: true,
      value: numeroInicial,
      placeholder: "Ex.: 529-7F3A9C2B",
      autocomplete: "off",
    }),
    campo("CPF ou CNPJ do titular", {
      name: "documento",
      required: true,
      inputmode: "numeric",
      autocomplete: "off",
    }),
    areaDoAviso,
    el("button", { type: "submit", classe: "primario" }, "Consultar"),
  );

  trocarConteudo(
    conteudo,
    el(
      "section",
      { classe: "cartao centralizado" },
      el("h1", {}, "Acompanhe o seu atendimento"),
      el("p", { classe: "suave" }, "Informe o número da OS que recebeu na oficina e o CPF ou CNPJ do titular."),
      formulario,
    ),
  );
  formulario.querySelector(numeroInicial ? "[name=documento]" : "[name=numero]").focus();
}

function mostrarAcompanhamento(os, consulta, mensagem) {
  const areaDoAviso = el("div", {}, mensagem);
  const decidir = async (rota, pergunta) => {
    if (!confirm(pergunta)) return;
    try {
      const atualizada = await chamarApi("POST", `/acompanhamento/${rota}`, consulta);
      const texto = rota === "aprovacao" ? "Orçamento aprovado. Obrigado!" : "Orçamento rejeitado. A OS foi cancelada.";
      mostrarAcompanhamento(atualizada, consulta, aviso(texto, "sucesso"));
    } catch (erro) {
      trocarConteudo(areaDoAviso, aviso(mensagemDoErro(erro)));
    }
  };

  const decisao =
    os.status === "AGUARDANDO_APROVACAO" &&
    el(
      "div",
      { classe: "cartao" },
      el("h2", {}, "Sua decisão"),
      el("p", {}, `Valor total do orçamento: ${moeda(os.valor_total)}.`),
      el(
        "div",
        { classe: "acoes" },
        el(
          "button",
          { classe: "primario", onclick: () => decidir("aprovacao", `Aprovar o orçamento de ${moeda(os.valor_total)}?`) },
          "Aprovar orçamento",
        ),
        el(
          "button",
          { classe: "perigo", onclick: () => decidir("rejeicao", "Rejeitar o orçamento? A OS será cancelada.") },
          "Rejeitar orçamento",
        ),
      ),
    );

  trocarConteudo(
    conteudo,
    el(
      "section",
      { classe: "centralizado" },
      areaDoAviso,
      el(
        "div",
        { classe: "cartao" },
        el("p", { classe: "suave" }, `OS ${os.numero}`),
        el("p", {}, selo(os.status)),
        el("p", {}, EXPLICACOES[os.status] ?? ""),
        el(
          "dl",
          { classe: "dados" },
          el("dt", {}, "Valor total"),
          el("dd", {}, os.valor_total === null ? "Orçamento em preparação" : moeda(os.valor_total)),
          el("dt", {}, "Previsão de entrega"),
          el("dd", {}, os.estimativa_entrega ? dataHora(os.estimativa_entrega) : "—"),
        ),
      ),
      decisao,
      el(
        "div",
        { classe: "cartao" },
        el("h2", {}, "Serviços"),
        os.servicos.length
          ? el("ul", {}, os.servicos.map((nome) => el("li", {}, nome)))
          : el("p", { classe: "suave" }, "Nenhum serviço incluído ainda."),
        os.pecas_pendentes.length > 0 && el("h2", {}, "Peças aguardando chegada"),
        os.pecas_pendentes.length > 0 &&
          el("ul", {}, os.pecas_pendentes.map((p) => el("li", {}, `${p.nome} (${p.quantidade})`))),
      ),
      el(
        "div",
        { classe: "acoes" },
        el("button", { onclick: () => atualizar(consulta, areaDoAviso) }, "Atualizar"),
        el("button", { classe: "discreto", onclick: () => mostrarFormulario(os.numero) }, "Consultar outra OS"),
      ),
    ),
  );
}

async function atualizar(consulta, areaDoAviso) {
  try {
    mostrarAcompanhamento(await chamarApi("POST", "/acompanhamento", consulta), consulta);
  } catch (erro) {
    trocarConteudo(areaDoAviso, aviso(mensagemDoErro(erro)));
  }
}

mostrarFormulario();
