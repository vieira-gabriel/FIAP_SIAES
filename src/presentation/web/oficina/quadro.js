// Quadro de OS: uma coluna por status, da abertura à finalização (RF-14).

import { chamarApi, consultaComFiltros } from "/comum/api.js";
import { NOMES_DOS_STATUS, campo, el, lerFormulario, moeda, trocarConteudo } from "/comum/dom.js";

const STATUS_EM_ANDAMENTO = [
  "RECEBIDA",
  "EM_DIAGNOSTICO",
  "AGUARDANDO_APROVACAO",
  "AGUARDANDO_PECA",
  "AGUARDANDO_EXECUCAO",
  "EM_EXECUCAO",
  "FINALIZADA",
];
const STATUS_ENCERRADOS = ["ENTREGUE", "CANCELADA"];

// O detalhamento da OS traz só o id do mecânico; a listagem traz o nome. O detalhe usa este
// mapa quando a OS foi aberta a partir do quadro.
export const nomeDoMecanicoPorOS = new Map();

const filtrosDoQuadro = { placa: "", documento: "", minhas: false, encerradas: false };

export async function mostrarQuadro(alvo, sessao) {
  const areaDoQuadro = el("div", {}, el("p", { classe: "suave" }, "Carregando..."));
  const filtros = el(
    "form",
    {
      classe: "linha cartao",
      onsubmit: (evento) => {
        evento.preventDefault();
        const dados = lerFormulario(filtros);
        Object.assign(filtrosDoQuadro, {
          placa: dados.placa,
          documento: dados.documento,
          minhas: dados.minhas === "on",
          encerradas: dados.encerradas === "on",
        });
        carregar(areaDoQuadro, sessao);
      },
    },
    campo("Placa", { name: "placa", value: filtrosDoQuadro.placa, placeholder: "ABC1D23" }),
    campo("CPF/CNPJ do cliente", { name: "documento", value: filtrosDoQuadro.documento }),
    sessao.perfil === "MECANICO" &&
      el(
        "label",
        { classe: "opcao" },
        el("input", { type: "checkbox", name: "minhas", checked: filtrosDoQuadro.minhas }),
        "Só as minhas",
      ),
    el(
      "label",
      { classe: "opcao" },
      el("input", { type: "checkbox", name: "encerradas", checked: filtrosDoQuadro.encerradas }),
      "Mostrar entregues e canceladas",
    ),
    el("button", { type: "submit", classe: "primario" }, "Atualizar"),
  );

  trocarConteudo(
    alvo,
    el(
      "div",
      { classe: "barra" },
      el("h1", {}, "Quadro de OS"),
      sessao.perfil !== "MECANICO" && el("a", { classe: "botao primario", href: "#/nova-os" }, "Nova OS"),
    ),
    filtros,
    areaDoQuadro,
  );
  await carregar(areaDoQuadro, sessao);
}

async function carregar(areaDoQuadro, sessao) {
  const ordens = await chamarApi(
    "GET",
    consultaComFiltros("/ordens-servico", {
      placa: filtrosDoQuadro.placa.trim().toUpperCase().replace(/[^A-Z0-9]/g, ""),
      documento: filtrosDoQuadro.documento.trim(),
      mecanico_id: filtrosDoQuadro.minhas && sessao.perfil === "MECANICO" ? sessao.usuarioId : "",
    }),
  );
  for (const os of ordens) nomeDoMecanicoPorOS.set(os.id, os.mecanico_nome);

  const status = filtrosDoQuadro.encerradas ? [...STATUS_EM_ANDAMENTO, ...STATUS_ENCERRADOS] : STATUS_EM_ANDAMENTO;
  trocarConteudo(
    areaDoQuadro,
    el(
      "div",
      { classe: "quadro" },
      status.map((s) => coluna(s, ordens.filter((os) => os.status === s))),
    ),
    el("p", { classe: "suave" }, `${ordens.length} OS encontradas. Atualizado às ${new Date().toLocaleTimeString("pt-BR")}.`),
  );
}

function coluna(status, ordens) {
  return el(
    "section",
    // No celular as colunas vazias somem, para a lista mostrar só o que tem OS.
    { classe: ordens.length ? "coluna" : "coluna sem-os", "aria-label": NOMES_DOS_STATUS[status] },
    el("h2", {}, NOMES_DOS_STATUS[status], el("span", { classe: "contador" }, ordens.length)),
    ordens.length ? ordens.map(cartaoDaOS) : el("p", { classe: "vazio" }, "Nenhuma OS."),
  );
}

function cartaoDaOS(os) {
  return el(
    "a",
    { classe: "cartao-os", href: `#/os/${os.id}` },
    el("strong", {}, os.placa),
    el("span", {}, os.cliente_nome),
    el("small", {}, os.numero),
    el("small", {}, os.mecanico_nome ? `Mecânico: ${os.mecanico_nome}` : "Sem mecânico"),
    os.valor_total !== null && el("small", {}, `Orçamento: ${moeda(os.valor_total)}`),
  );
}
