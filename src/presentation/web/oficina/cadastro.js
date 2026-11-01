// Tela de cadastro com lista, formulário de inclusão e edição, e exclusão.
//
// Cada recurso informa as colunas, os campos e como o formulário vira o corpo da requisição.

import { chamarApi } from "/comum/api.js";
import { aviso, campo, campoDeSelecao, el, executarComAviso, lerFormulario, trocarConteudo } from "/comum/dom.js";

/**
 * @param {object} recurso
 * @param {string} recurso.titulo
 * @param {string} recurso.caminho  rota da API, como "/servicos"
 * @param {string} recurso.nome  nome do item no singular, para as mensagens
 * @param {boolean} [recurso.feminino]  concordância das mensagens ("Nova peça", "Peça excluída")
 * @param {Array<[string, (item) => any, string?]>} recurso.colunas  título, valor e classe
 * @param {Array<object>} recurso.campos  atributos do input, com `rotulo` e, num select, `opcoes`
 * @param {(dados, edicao: boolean) => object} recurso.paraCorpo
 * @param {boolean} recurso.podeCriar
 * @param {boolean} recurso.podeEditar
 * @param {boolean} recurso.podeExcluir
 * @param {(item, recarregar) => Node[]} [recurso.acoesExtras]
 * @param {(item) => boolean} [recurso.inativo]
 * @param {(item, recarregar) => Promise<Node>} [recurso.detalheDaLinha]  conteúdo abaixo da linha
 */
export async function mostrarCadastro(alvo, recurso, mensagem) {
  const itens = await chamarApi("GET", recurso.caminho);
  const recarregar = (texto) => mostrarCadastro(alvo, recurso, texto && aviso(texto, "sucesso"));
  const areaDoAviso = el("div", {}, mensagem);
  const areaDoFormulario = el("div");

  const abrirFormulario = (item) => {
    trocarConteudo(areaDoFormulario, formularioDoItem(recurso, item, areaDoAviso, recarregar, () => trocarConteudo(areaDoFormulario)));
    areaDoFormulario.querySelector("input, select")?.focus();
  };

  const linhas = itens.flatMap((item) => {
    const detalhe = recurso.detalheDaLinha && el("tr", { hidden: true }, el("td", { colspan: recurso.colunas.length + 1 }));
    const linha = el(
      "tr",
      { classe: recurso.inativo?.(item) ? "inativo" : null },
      recurso.colunas.map(([, valor, classe]) => el("td", { classe }, valor(item))),
      el(
        "td",
        {},
        el(
          "div",
          { classe: "acoes" },
          detalhe &&
            el(
              "button",
              {
                classe: "discreto",
                onclick: async () => {
                  detalhe.hidden = !detalhe.hidden;
                  if (!detalhe.hidden) trocarConteudo(detalhe.firstChild, await recurso.detalheDaLinha(item, recarregar));
                },
              },
              "Ver",
            ),
          recurso.podeEditar && el("button", { classe: "discreto", onclick: () => abrirFormulario(item) }, "Editar"),
          recurso.acoesExtras?.(item, recarregar, areaDoAviso),
          recurso.podeExcluir &&
            el(
              "button",
              {
                classe: "discreto perigo",
                onclick: async () => {
                  if (!confirm(`Excluir ${recurso.nome} "${item.nome ?? item.placa}"?`)) return;
                  const { ok } = await executarComAviso(areaDoAviso, () => chamarApi("DELETE", `${recurso.caminho}/${item.id}`));
                  if (ok) recarregar(`${capitalizar(recurso.nome)} ${flexionar(recurso, "excluído")}.`);
                },
              },
              "Excluir",
            ),
        ),
      ),
    );
    return detalhe ? [linha, detalhe] : [linha];
  });

  trocarConteudo(
    alvo,
    el(
      "div",
      { classe: "barra" },
      el("h1", {}, recurso.titulo),
      recurso.podeCriar && el("button", { classe: "primario", onclick: () => abrirFormulario(null) }, `${flexionar(recurso, "Novo")} ${recurso.nome}`),
    ),
    areaDoAviso,
    areaDoFormulario,
    el(
      "section",
      { classe: "cartao" },
      itens.length
        ? el(
            "div",
            { classe: "tabela-rolavel" },
            el(
              "table",
              {},
              el("thead", {}, el("tr", {}, recurso.colunas.map(([titulo, , classe]) => el("th", { classe }, titulo)), el("th", {}))),
              el("tbody", {}, linhas),
            ),
          )
        : el("p", { classe: "suave" }, "Nenhum registro."),
    ),
  );
}

function formularioDoItem(recurso, item, areaDoAviso, recarregar, fechar) {
  const edicao = item !== null;
  const campos = recurso.campos.filter((c) => (edicao ? !c.somenteNaInclusao : !c.somenteNaEdicao));
  const formulario = el(
    "form",
    {
      onsubmit: async (evento) => {
        evento.preventDefault();
        const corpo = recurso.paraCorpo(lerFormulario(formulario), edicao);
        const { ok } = await executarComAviso(areaDoAviso, () =>
          edicao ? chamarApi("PUT", `${recurso.caminho}/${item.id}`, corpo) : chamarApi("POST", recurso.caminho, corpo),
        );
        if (ok) recarregar(`${capitalizar(recurso.nome)} ${flexionar(recurso, edicao ? "atualizado" : "cadastrado")}.`);
      },
    },
    el(
      "div",
      { classe: "linha" },
      campos.map(({ rotulo, opcoes, somenteNaInclusao, somenteNaEdicao, ...atributos }) =>
        opcoes
          ? campoDeSelecao(rotulo, atributos.name, opcoes, { required: true })
          : campo(rotulo, { ...atributos, value: edicao ? (item[atributos.name] ?? "") : (atributos.value ?? "") }),
      ),
    ),
    el(
      "div",
      { classe: "acoes" },
      el("button", { type: "submit", classe: "primario" }, edicao ? "Salvar" : "Cadastrar"),
      el("button", { type: "button", onclick: fechar }, "Cancelar"),
    ),
  );
  if (edicao) {
    for (const { name, opcoes } of campos) if (opcoes) formulario.elements[name].value = item[name];
  }
  return el("section", { classe: "cartao" }, el("h2", {}, edicao ? `Editar ${recurso.nome}` : `${flexionar(recurso, "Novo")} ${recurso.nome}`), formulario);
}

function flexionar(recurso, palavraNoMasculino) {
  return recurso.feminino ? palavraNoMasculino.replace(/o$/, "a") : palavraNoMasculino;
}

function capitalizar(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}
