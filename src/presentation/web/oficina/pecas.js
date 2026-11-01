// Peças e estoque (RF-12): a reposição e o ajuste liberam as OS que esperavam a peça (RF-19).

import { chamarApi } from "/comum/api.js";
import { el, executarComAviso, moeda } from "/comum/dom.js";
import { mostrarCadastro } from "/oficina/cadastro.js";
import { GERENTE, OFICINA, pode } from "/oficina/perfis.js";

export function mostrarPecas(alvo, sessao) {
  const gerente = pode(sessao, GERENTE);
  return mostrarCadastro(alvo, {
    titulo: "Peças e estoque",
    caminho: "/pecas",
    nome: "peça",
    feminino: true,
    colunas: [
      ["Código", (p) => p.codigo_referencia],
      ["Nome", (p) => p.nome],
      ["Preço", (p) => moeda(p.preco_unitario), "numero"],
      ["Reposição", (p) => `${p.prazo_reposicao_dias} d`, "numero"],
      ["Física", (p) => p.quantidade_fisica, "numero"],
      ["Reservada", (p) => p.quantidade_reservada, "numero"],
      ["Saldo", (p) => el("strong", {}, p.saldo_disponivel), "numero"],
    ],
    campos: [
      { rotulo: "Código de referência", name: "codigo_referencia", required: true },
      { rotulo: "Nome", name: "nome", required: true },
      { rotulo: "Preço unitário (R$)", name: "preco_unitario", required: true, inputmode: "decimal", placeholder: "35.90" },
      { rotulo: "Prazo de reposição (dias)", name: "prazo_reposicao_dias", type: "number", min: 0, required: true },
      {
        rotulo: "Quantidade inicial",
        name: "quantidade_fisica_inicial",
        type: "number",
        min: 0,
        value: 0,
        somenteNaInclusao: true,
      },
    ],
    paraCorpo: (dados, edicao) => {
      const corpo = {
        codigo_referencia: dados.codigo_referencia,
        nome: dados.nome,
        preco_unitario: dados.preco_unitario.replace(",", "."),
        prazo_reposicao_dias: Number(dados.prazo_reposicao_dias),
      };
      if (!edicao) corpo.quantidade_fisica_inicial = Number(dados.quantidade_fisica_inicial || 0);
      return corpo;
    },
    podeCriar: gerente,
    podeEditar: gerente,
    podeExcluir: gerente,
    acoesExtras: pode(sessao, OFICINA) ? acoesDeEstoque : undefined,
  });
}

function acoesDeEstoque(peca, recarregar, areaDoAviso) {
  const movimentar = async (pergunta, metodo, caminho, campo, sucesso) => {
    const resposta = prompt(pergunta);
    if (resposta === null) return;
    const quantidade = Number(resposta);
    if (!Number.isInteger(quantidade)) {
      alert("Informe um número inteiro.");
      return;
    }
    const { ok } = await executarComAviso(areaDoAviso, () => chamarApi(metodo, `/pecas/${peca.id}/${caminho}`, { [campo]: quantidade }));
    if (ok) recarregar(sucesso);
  };
  return [
    el(
      "button",
      {
        classe: "discreto",
        onclick: () =>
          movimentar(`Quantas unidades de "${peca.nome}" chegaram?`, "POST", "reposicao", "quantidade", "Reposição registrada. As OS que esperavam a peça foram atendidas pela ordem de abertura."),
      },
      "Repor",
    ),
    el(
      "button",
      {
        classe: "discreto",
        onclick: () =>
          movimentar(
            `Quantidade física contada de "${peca.nome}" (hoje ${peca.quantidade_fisica}, com ${peca.quantidade_reservada} reservadas):`,
            "PUT",
            "quantidade-fisica",
            "quantidade_fisica",
            "Quantidade física ajustada.",
          ),
      },
      "Ajustar",
    ),
  ];
}
