// Catálogo de serviços (RF-10, RF-11).

import { moeda } from "/comum/dom.js";
import { mostrarCadastro } from "/oficina/cadastro.js";
import { GERENTE, pode } from "/oficina/perfis.js";

export function mostrarServicos(alvo, sessao) {
  const gerente = pode(sessao, GERENTE);
  return mostrarCadastro(alvo, {
    titulo: "Catálogo de serviços",
    caminho: "/servicos",
    nome: "serviço",
    colunas: [
      ["Código", (s) => s.codigo],
      ["Nome", (s) => s.nome],
      ["Descrição", (s) => s.descricao],
      ["Tempo", (s) => `${s.tempo_estimado_minutos} min`, "numero"],
      ["Valor", (s) => moeda(s.valor_base), "numero"],
    ],
    campos: [
      { rotulo: "Código", name: "codigo", required: true },
      { rotulo: "Nome", name: "nome", required: true },
      { rotulo: "Descrição", name: "descricao", required: true },
      { rotulo: "Valor (R$)", name: "valor_base", required: true, inputmode: "decimal", placeholder: "120.00" },
      { rotulo: "Tempo estimado (min)", name: "tempo_estimado_minutos", type: "number", min: 1, required: true },
    ],
    // O valor vai como texto, com ponto decimal, para não perder centavos (RNF-11).
    paraCorpo: (dados) => ({
      ...dados,
      valor_base: dados.valor_base.replace(",", "."),
      tempo_estimado_minutos: Number(dados.tempo_estimado_minutos),
    }),
    podeCriar: gerente,
    podeEditar: gerente,
    podeExcluir: gerente,
  });
}
