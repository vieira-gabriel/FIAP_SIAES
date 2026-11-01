// Frente da Loja: login, menu por perfil e navegação entre as telas pelo "#" da URL.
//
// O menu só esconde o que o perfil não pode fazer; quem decide a permissão é a API (RNF-03).

import { chamarApi, guardarToken, lerSessao, quandoPerderASessao } from "/comum/api.js";
import { NOMES_DOS_PERFIS, aviso, campo, el, lerFormulario, trocarConteudo } from "/comum/dom.js";
import { mostrarClientes } from "/oficina/clientes.js";
import { mostrarDetalheDaOS } from "/oficina/detalhe_os.js";
import { mostrarNovaOS } from "/oficina/nova_os.js";
import { mostrarPecas } from "/oficina/pecas.js";
import { mostrarQuadro } from "/oficina/quadro.js";
import { mostrarRelatorio } from "/oficina/relatorio.js";
import { mostrarServicos } from "/oficina/servicos.js";
import { TODOS, ATENDIMENTO, GERENTE } from "/oficina/perfis.js";
import { mostrarUsuarios } from "/oficina/usuarios.js";

const conteudo = document.getElementById("conteudo");
const menu = document.getElementById("menu");
const areaDaSessao = document.getElementById("sessao");

const TELAS = [
  { rota: "quadro", titulo: "Quadro de OS", perfis: TODOS, mostrar: mostrarQuadro },
  { rota: "nova-os", titulo: "Nova OS", perfis: ATENDIMENTO, mostrar: mostrarNovaOS },
  { rota: "clientes", titulo: "Clientes", perfis: TODOS, mostrar: mostrarClientes },
  { rota: "servicos", titulo: "Serviços", perfis: TODOS, mostrar: mostrarServicos },
  { rota: "pecas", titulo: "Peças e estoque", perfis: TODOS, mostrar: mostrarPecas },
  { rota: "usuarios", titulo: "Usuários", perfis: GERENTE, mostrar: mostrarUsuarios },
  { rota: "relatorio", titulo: "Relatório", perfis: GERENTE, mostrar: mostrarRelatorio },
  { rota: "os", perfis: TODOS, mostrar: mostrarDetalheDaOS },
];

function rotaAtual() {
  const [rota = "quadro", parametro] = location.hash.replace(/^#\/?/, "").split("/");
  return { rota: rota || "quadro", parametro };
}

function montarMenu(sessao) {
  const { rota } = rotaAtual();
  trocarConteudo(
    menu,
    TELAS.filter((tela) => tela.titulo && tela.perfis.includes(sessao.perfil)).map((tela) =>
      el("a", { href: `#/${tela.rota}`, "aria-current": tela.rota === rota ? "page" : null }, tela.titulo),
    ),
  );
  trocarConteudo(
    areaDaSessao,
    el("span", {}, NOMES_DOS_PERFIS[sessao.perfil] ?? sessao.perfil),
    el("button", { classe: "discreto", onclick: sair }, "Sair"),
  );
}

async function navegar() {
  const sessao = lerSessao();
  if (!sessao) return mostrarLogin();
  montarMenu(sessao);

  const { rota, parametro } = rotaAtual();
  const tela = TELAS.find((t) => t.rota === rota && t.perfis.includes(sessao.perfil));
  if (!tela) {
    location.hash = "#/quadro";
    return;
  }
  trocarConteudo(conteudo, el("p", { classe: "suave" }, "Carregando..."));
  try {
    await tela.mostrar(conteudo, sessao, parametro);
  } catch (erro) {
    if (erro.status !== 401) trocarConteudo(conteudo, aviso(erro.mensagemCompleta ?? erro.message));
  }
}

function sair() {
  guardarToken(null);
  location.hash = "";
  mostrarLogin();
}

function mostrarLogin(mensagem) {
  trocarConteudo(menu);
  trocarConteudo(areaDaSessao);
  const areaDoAviso = el("div", {}, mensagem && aviso(mensagem, "info"));
  const formulario = el(
    "form",
    {
      onsubmit: async (evento) => {
        evento.preventDefault();
        const botao = formulario.querySelector("button");
        botao.disabled = true;
        try {
          const { access_token } = await chamarApi("POST", "/auth/login", lerFormulario(formulario));
          guardarToken(access_token);
          if (!location.hash || location.hash === "#") location.hash = "#/quadro";
          else navegar();
        } catch (erro) {
          trocarConteudo(areaDoAviso, aviso(erro.message));
          botao.disabled = false;
        }
      },
    },
    campo("E-mail", { name: "email", type: "email", required: true, autocomplete: "username" }),
    campo("Senha", { name: "senha", type: "password", required: true, autocomplete: "current-password" }),
    areaDoAviso,
    el("button", { type: "submit", classe: "primario" }, "Entrar"),
  );
  trocarConteudo(
    conteudo,
    el(
      "section",
      { classe: "cartao centralizado" },
      el("h1", {}, "Entrar na oficina"),
      el("p", { classe: "suave" }, "Acesso para atendentes, mecânicos e gerentes."),
      formulario,
      el("p", { classe: "suave" }, "Cliente? ", el("a", { href: "/cliente/" }, "Acompanhe a sua OS aqui"), "."),
    ),
  );
  formulario.querySelector("input").focus();
}

quandoPerderASessao(() => mostrarLogin("A sessão expirou. Entre de novo."));
window.addEventListener("hashchange", navegar);
navegar();
