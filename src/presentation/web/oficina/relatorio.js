// Relatório de tempos médios por mês da finalização, só para o Gerente (RF-27).

import { chamarApi, consultaComFiltros } from "/comum/api.js";
import { campo, duracao, el, executarComAviso, lerFormulario, trocarConteudo } from "/comum/dom.js";

// O <input type="date"> não tem fuso; a API exige data e hora com fuso. O início vale do primeiro
// instante do dia e o fim até o último, no fuso do navegador.
function inicioDoDia(data) {
  return data ? new Date(`${data}T00:00:00`).toISOString() : "";
}

function fimDoDia(data) {
  return data ? new Date(`${data}T23:59:59.999`).toISOString() : "";
}

export async function mostrarRelatorio(alvo) {
  const areaDoAviso = el("div");
  const areaDoResultado = el("div");

  const gerar = async () => {
    const dados = lerFormulario(formulario);
    const { ok, resultado } = await executarComAviso(areaDoAviso, () =>
      chamarApi(
        "GET",
        consultaComFiltros("/relatorios/tempos-medios", {
          finalizadas_de: inicioDoDia(dados.de),
          finalizadas_ate: fimDoDia(dados.ate),
        }),
      ),
    );
    if (ok) trocarConteudo(areaDoResultado, tabelas(resultado));
  };

  const formulario = el(
    "form",
    {
      classe: "linha cartao",
      onsubmit: (evento) => {
        evento.preventDefault();
        gerar();
      },
    },
    campo("Finalizadas de", { name: "de", type: "date" }),
    campo("Até", { name: "ate", type: "date" }),
    el("button", { type: "submit", classe: "primario" }, "Gerar"),
  );

  trocarConteudo(
    alvo,
    el("div", { classe: "barra" }, el("h1", {}, "Tempos médios")),
    el("p", { classe: "suave" }, "Agrupado pelo mês da finalização (UTC). Sem datas, considera todas as OS finalizadas."),
    formulario,
    areaDoAviso,
    areaDoResultado,
  );
  await gerar();
}

function tabelas(relatorio) {
  return el(
    "div",
    { classe: "grade-2" },
    tabela("Execução por mecânico", relatorio.execucao, true),
    tabela("Espera por peça", relatorio.espera_por_peca),
    tabela("Tempo total (abertura à finalização)", relatorio.total),
  );
}

function tabela(titulo, linhas, comMecanico = false) {
  return el(
    "section",
    { classe: "cartao" },
    el("h2", {}, titulo),
    linhas.length
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
                el("th", {}, "Mês"),
                comMecanico && el("th", {}, "Mecânico"),
                el("th", { classe: "numero" }, "OS"),
                el("th", { classe: "numero" }, "Média"),
              ),
            ),
            el(
              "tbody",
              {},
              linhas.map((l) =>
                el(
                  "tr",
                  {},
                  el("td", {}, l.periodo),
                  comMecanico && el("td", {}, l.mecanico_nome ?? "—"),
                  el("td", { classe: "numero" }, l.quantidade_os),
                  el("td", { classe: "numero" }, duracao(l.tempo_medio_segundos)),
                ),
              ),
            ),
          ),
        )
      : el("p", { classe: "suave" }, "Sem OS no período."),
  );
}
