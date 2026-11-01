// Mesmos grupos de perfis das rotas da API (tests/integration/test_permissoes_das_rotas.py).

export const TODOS = ["ATENDENTE", "MECANICO", "GERENTE"];
export const ATENDIMENTO = ["ATENDENTE", "GERENTE"];
export const OFICINA = ["MECANICO", "GERENTE"];
export const GERENTE = ["GERENTE"];

export function pode(sessao, perfis) {
  return perfis.includes(sessao.perfil);
}
