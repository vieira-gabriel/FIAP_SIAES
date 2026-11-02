// Montagem do DOM e formatação dos valores da API.
//
// Todo texto entra por `textContent`, nunca por `innerHTML`: um nome de cliente com marcação
// aparece como texto e não vira HTML (RNF-04).

export function el(tag, atributos = {}, ...filhos) {
  const elemento = document.createElement(tag);
  for (const [nome, valor] of Object.entries(atributos ?? {})) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (nome.startsWith("on")) elemento.addEventListener(nome.slice(2), valor);
    else if (nome === "classe") elemento.className = valor;
    else if (valor === true) elemento.setAttribute(nome, "");
    else elemento.setAttribute(nome, valor);
  }
  for (const filho of filhos.flat()) {
    if (filho === undefined || filho === null || filho === false) continue;
    elemento.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return elemento;
}

export function trocarConteudo(alvo, ...filhos) {
  alvo.replaceChildren(...filhos.flat().filter(Boolean));
}

export const NOMES_DOS_STATUS = {
  RECEBIDA: "Recebida",
  EM_DIAGNOSTICO: "Em diagnóstico",
  AGUARDANDO_APROVACAO: "Aguardando aprovação",
  AGUARDANDO_PECA: "Aguardando peça",
  AGUARDANDO_EXECUCAO: "Aguardando execução",
  EM_EXECUCAO: "Em execução",
  FINALIZADA: "Finalizada",
  ENTREGUE: "Entregue",
  CANCELADA: "Cancelada",
};

export const NOMES_DOS_PERFIS = {
  ATENDENTE: "Atendente",
  MECANICO: "Mecânico",
  GERENTE: "Gerente",
};

export function selo(status) {
  return el("span", { classe: `selo selo-${status.toLowerCase()}` }, NOMES_DOS_STATUS[status] ?? status);
}

const MOEDA = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const DATA_E_HORA = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

// Os valores monetários chegam como texto ("120.50") para não perder centavos (RNF-11); a
// conversão para número aqui serve só para exibir.
export function moeda(valor) {
  return valor === null || valor === undefined ? "—" : MOEDA.format(Number(valor));
}

export function dataHora(valor) {
  return valor ? DATA_E_HORA.format(new Date(valor)) : "—";
}

export function duracao(segundos) {
  if (segundos < 60) return `${Math.round(segundos)} s`;
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `${horas} h ${minutos % 60} min`;
  return `${Math.floor(horas / 24)} d ${horas % 24} h`;
}

export function aviso(mensagem, tipo = "erro") {
  return el("p", { classe: `aviso aviso-${tipo}`, role: tipo === "erro" ? "alert" : "status" }, mensagem);
}

// Mostra a mensagem da API na área do formulário e devolve se a operação deu certo.
export async function executarComAviso(areaDoAviso, operacao, mensagemDeSucesso) {
  trocarConteudo(areaDoAviso);
  try {
    const resultado = await operacao();
    if (mensagemDeSucesso) trocarConteudo(areaDoAviso, aviso(mensagemDeSucesso, "sucesso"));
    return { ok: true, resultado };
  } catch (erro) {
    trocarConteudo(areaDoAviso, aviso(erro.mensagemCompleta ?? erro.message));
    return { ok: false, erro };
  }
}

export function lerFormulario(formulario) {
  return Object.fromEntries(new FormData(formulario).entries());
}

export function campo(rotulo, atributos) {
  return el("label", { classe: "campo" }, el("span", {}, rotulo), el("input", atributos));
}

export function campoDeSelecao(rotulo, nome, opcoes, atributos = {}) {
  return el(
    "label",
    { classe: "campo" },
    el("span", {}, rotulo),
    el(
      "select",
      { name: nome, ...atributos },
      opcoes.map(([valor, texto]) => el("option", { value: valor }, texto)),
    ),
  );
}

export function apenasDigitos(texto) {
  return (texto ?? "").replace(/\D/g, "");
}
