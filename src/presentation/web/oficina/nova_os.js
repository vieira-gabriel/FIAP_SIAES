// Abertura da OS no balcão (RF-13): cliente e veículo novos são cadastrados junto com a OS.
//
// A tela consulta o cadastro ao sair dos campos de documento e placa só para mostrar os campos
// que faltam; quem decide se o cliente e o veículo existem é a rota de abertura.

import { chamarApi, consultaComFiltros } from "/comum/api.js";
import { apenasDigitos, aviso, campo, el, executarComAviso, lerFormulario, trocarConteudo } from "/comum/dom.js";

function normalizarPlaca(placa) {
  return (placa ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

export async function mostrarNovaOS(alvo) {
  const clientes = await chamarApi("GET", "/clientes");
  const areaDoAviso = el("div");
  const situacaoDoCliente = el("p", { classe: "suave" });
  const situacaoDoVeiculo = el("p", { classe: "suave" });

  const dadosDoCliente = el(
    "fieldset",
    { hidden: true },
    el("legend", {}, "Cliente novo"),
    el(
      "div",
      { classe: "linha" },
      campo("Nome", { name: "cliente_nome" }),
      campo("E-mail", { name: "cliente_email", type: "email" }),
      campo("Telefone", { name: "cliente_telefone", inputmode: "tel" }),
    ),
  );
  const dadosDoVeiculo = el(
    "fieldset",
    { hidden: true },
    el("legend", {}, "Veículo novo"),
    el(
      "div",
      { classe: "linha" },
      campo("Marca", { name: "veiculo_marca" }),
      campo("Modelo", { name: "veiculo_modelo" }),
      campo("Ano", { name: "veiculo_ano", type: "number", min: 1900, max: 2100 }),
    ),
  );

  let clienteEncontrado = null;

  const exibirGrupo = (grupo, visivel) => {
    grupo.hidden = !visivel;
    for (const entrada of grupo.querySelectorAll("input")) entrada.required = visivel;
  };

  const conferirCliente = () => {
    const digitos = apenasDigitos(formulario.documento.value);
    clienteEncontrado = digitos ? clientes.find((c) => apenasDigitos(c.documento) === digitos) : null;
    if (!digitos) situacaoDoCliente.textContent = "";
    else if (clienteEncontrado) situacaoDoCliente.textContent = `Cliente cadastrado: ${clienteEncontrado.nome}.`;
    else situacaoDoCliente.textContent = "Cliente sem cadastro: preencha os dados abaixo.";
    exibirGrupo(dadosDoCliente, Boolean(digitos) && !clienteEncontrado);
    return conferirVeiculo();
  };

  const conferirVeiculo = async () => {
    const placa = normalizarPlaca(formulario.placa.value);
    if (!placa) {
      situacaoDoVeiculo.textContent = "";
      return exibirGrupo(dadosDoVeiculo, false);
    }
    const veiculos = clienteEncontrado
      ? await chamarApi("GET", consultaComFiltros("/veiculos", { cliente_id: clienteEncontrado.id }))
      : [];
    const veiculo = veiculos.find((v) => normalizarPlaca(v.placa) === placa);
    situacaoDoVeiculo.textContent = veiculo
      ? `Veículo cadastrado: ${veiculo.marca} ${veiculo.modelo} (${veiculo.ano}).`
      : "Veículo sem cadastro neste cliente: preencha os dados abaixo.";
    exibirGrupo(dadosDoVeiculo, !veiculo);
  };

  const formulario = el(
    "form",
    {
      onsubmit: async (evento) => {
        evento.preventDefault();
        const dados = lerFormulario(formulario);
        const corpo = { documento: dados.documento, placa: normalizarPlaca(dados.placa) };
        if (!dadosDoCliente.hidden) {
          corpo.cliente = { nome: dados.cliente_nome, email: dados.cliente_email, telefone: dados.cliente_telefone };
        }
        if (!dadosDoVeiculo.hidden) {
          corpo.veiculo = { marca: dados.veiculo_marca, modelo: dados.veiculo_modelo, ano: Number(dados.veiculo_ano) };
        }
        const { ok, resultado } = await executarComAviso(areaDoAviso, () => chamarApi("POST", "/ordens-servico", corpo));
        if (ok) location.hash = `#/os/${resultado.id}`;
      },
    },
    el(
      "div",
      { classe: "linha" },
      campo("CPF ou CNPJ do cliente", { name: "documento", required: true, onchange: conferirCliente, autocomplete: "off" }),
      campo("Placa", { name: "placa", required: true, placeholder: "ABC1D23", onchange: conferirVeiculo, autocomplete: "off" }),
    ),
    situacaoDoCliente,
    dadosDoCliente,
    situacaoDoVeiculo,
    dadosDoVeiculo,
    areaDoAviso,
    el("div", { classe: "acoes" }, el("button", { type: "submit", classe: "primario" }, "Abrir OS"), el("a", { href: "#/quadro", classe: "botao" }, "Voltar")),
  );

  trocarConteudo(
    alvo,
    el("div", { classe: "barra" }, el("h1", {}, "Nova ordem de serviço")),
    el("section", { classe: "cartao" }, formulario),
    clientes.length === 0 && aviso("Nenhum cliente cadastrado ainda: a abertura cadastra o primeiro.", "info"),
  );
  formulario.documento.focus();
}
