// Gestão de usuários, só para o Gerente (RF-03).

import { chamarApi } from "/comum/api.js";
import { NOMES_DOS_PERFIS, el, executarComAviso } from "/comum/dom.js";
import { mostrarCadastro } from "/oficina/cadastro.js";

const OPCOES_DE_PERFIL = Object.entries(NOMES_DOS_PERFIS);

export function mostrarUsuarios(alvo, sessao) {
  return mostrarCadastro(alvo, {
    titulo: "Usuários",
    caminho: "/usuarios",
    nome: "usuário",
    colunas: [
      ["Nome", (u) => (u.id === sessao.usuarioId ? `${u.nome} (você)` : u.nome)],
      ["E-mail", (u) => u.email],
      ["Perfil", (u) => NOMES_DOS_PERFIS[u.perfil] ?? u.perfil],
      ["Situação", (u) => (u.ativo ? "Ativo" : "Desativado")],
    ],
    campos: [
      { rotulo: "Nome", name: "nome", required: true },
      { rotulo: "E-mail", name: "email", type: "email", required: true },
      { rotulo: "Perfil", name: "perfil", opcoes: OPCOES_DE_PERFIL },
      {
        rotulo: "Senha (mínimo 8 caracteres)",
        name: "senha",
        type: "password",
        minlength: 8,
        required: true,
        autocomplete: "new-password",
        somenteNaInclusao: true,
      },
    ],
    paraCorpo: (dados) => dados,
    podeCriar: true,
    podeEditar: true,
    podeExcluir: false,
    inativo: (u) => !u.ativo,
    acoesExtras: (usuario, recarregar, areaDoAviso) => acoesDoUsuario(usuario, recarregar, areaDoAviso),
  });
}

function acoesDoUsuario(usuario, recarregar, areaDoAviso) {
  const trocarSenha = async () => {
    const senha = prompt(`Nova senha de ${usuario.nome} (mínimo 8 caracteres):`);
    if (!senha) return;
    const { ok } = await executarComAviso(areaDoAviso, () => chamarApi("PUT", `/usuarios/${usuario.id}/senha`, { senha }));
    if (ok) recarregar("Senha alterada.");
  };
  const alternarAcesso = async () => {
    const acao = usuario.ativo ? "desativar" : "reativar";
    if (!confirm(`Deseja ${acao} o acesso de ${usuario.nome}?`)) return;
    const { ok } = await executarComAviso(areaDoAviso, () => chamarApi("POST", `/usuarios/${usuario.id}/${acao}`));
    if (ok) recarregar(usuario.ativo ? "Acesso desativado." : "Acesso reativado.");
  };
  return [
    el("button", { classe: "discreto", onclick: trocarSenha }, "Senha"),
    el("button", { classe: usuario.ativo ? "discreto perigo" : "discreto", onclick: alternarAcesso }, usuario.ativo ? "Desativar" : "Reativar"),
  ];
}
