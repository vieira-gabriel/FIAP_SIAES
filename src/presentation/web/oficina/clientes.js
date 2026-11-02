// Clientes e veículos (RF-04 a RF-09).

import { chamarApi, consultaComFiltros } from "/comum/api.js";
import { campo, el, executarComAviso, lerFormulario, trocarConteudo } from "/comum/dom.js";
import { mostrarCadastro } from "/oficina/cadastro.js";
import { ATENDIMENTO, GERENTE, pode } from "/oficina/perfis.js";

export function mostrarClientes(alvo, sessao) {
  return mostrarCadastro(alvo, {
    titulo: "Clientes",
    caminho: "/clientes",
    nome: "cliente",
    colunas: [
      ["Nome", (c) => c.nome],
      ["CPF/CNPJ", (c) => c.documento],
      ["E-mail", (c) => c.email],
      ["Telefone", (c) => c.telefone],
    ],
    campos: [
      { rotulo: "Nome", name: "nome", required: true },
      { rotulo: "CPF ou CNPJ", name: "documento", required: true },
      { rotulo: "E-mail", name: "email", type: "email", required: true },
      { rotulo: "Telefone", name: "telefone", required: true, inputmode: "tel" },
    ],
    paraCorpo: (dados) => dados,
    podeCriar: pode(sessao, ATENDIMENTO),
    podeEditar: pode(sessao, ATENDIMENTO),
    podeExcluir: pode(sessao, GERENTE),
    detalheDaLinha: (cliente) => veiculosDoCliente(cliente, sessao),
  });
}

async function veiculosDoCliente(cliente, sessao) {
  const area = el("div");
  const areaDoAviso = el("div");
  const editavel = pode(sessao, ATENDIMENTO);

  const recarregar = async () => trocarConteudo(area, await veiculosDoCliente(cliente, sessao));
  const veiculos = await chamarApi("GET", consultaComFiltros("/veiculos", { cliente_id: cliente.id }));

  const formulario =
    editavel &&
    el(
      "form",
      {
        classe: "linha",
        onsubmit: async (evento) => {
          evento.preventDefault();
          const dados = lerFormulario(formulario);
          const { ok } = await executarComAviso(areaDoAviso, () =>
            chamarApi("POST", "/veiculos", {
              ...dados,
              placa: dados.placa.toUpperCase().replace(/[^A-Z0-9]/g, ""),
              ano: Number(dados.ano),
              cliente_id: cliente.id,
            }),
          );
          if (ok) await recarregar();
        },
      },
      campo("Placa", { name: "placa", required: true, placeholder: "ABC1D23" }),
      campo("Marca", { name: "marca", required: true }),
      campo("Modelo", { name: "modelo", required: true }),
      campo("Ano", { name: "ano", type: "number", min: 1900, max: 2100, required: true }),
      el("button", { type: "submit" }, "Incluir veículo"),
    );

  trocarConteudo(
    area,
    el("h3", {}, `Veículos de ${cliente.nome}`),
    veiculos.length
      ? el(
          "ul",
          {},
          veiculos.map((v) =>
            el(
              "li",
              {},
              `${v.placa} · ${v.marca} ${v.modelo} (${v.ano}) `,
              editavel &&
                el(
                  "button",
                  {
                    classe: "discreto perigo",
                    onclick: async () => {
                      if (!confirm(`Excluir o veículo ${v.placa}?`)) return;
                      const { ok } = await executarComAviso(areaDoAviso, () => chamarApi("DELETE", `/veiculos/${v.id}`));
                      if (ok) await recarregar();
                    },
                  },
                  "Excluir",
                ),
            ),
          ),
        )
      : el("p", { classe: "suave" }, "Nenhum veículo."),
    areaDoAviso,
    formulario,
  );
  return area;
}
