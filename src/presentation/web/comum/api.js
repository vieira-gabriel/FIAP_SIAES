// Chamadas à API da mesma origem, com o corpo de erro único `ErroResponse` (guia §5.5).

const CHAVE_DO_TOKEN = "siaes.token";

export class ErroDaApi extends Error {
  constructor(status, corpo, cabecalhos) {
    super(corpo?.mensagem ?? `Erro ${status} ao falar com o servidor.`);
    this.status = status;
    this.codigo = corpo?.codigo ?? "ERRO_DESCONHECIDO";
    this.detalhes = corpo?.detalhes ?? [];
    this.retryAfter = Number(cabecalhos?.get("Retry-After")) || null;
  }

  // Junta os campos de um 422 ENTRADA_INVALIDA à mensagem, para o usuário saber o que corrigir.
  get mensagemCompleta() {
    if (!this.detalhes.length) return this.message;
    const campos = this.detalhes.map((d) => `${d.campo}: ${d.mensagem}`).join("; ");
    return `${this.message} (${campos})`;
  }
}

// O sessionStorage pode estar bloqueado (janela privada, política do navegador); sem ele o login
// vale só até a página ser recarregada.
let tokenEmMemoria = null;

export function lerToken() {
  try {
    return sessionStorage.getItem(CHAVE_DO_TOKEN) ?? tokenEmMemoria;
  } catch {
    return tokenEmMemoria;
  }
}

export function guardarToken(token) {
  tokenEmMemoria = token;
  try {
    if (token) sessionStorage.setItem(CHAVE_DO_TOKEN, token);
    else sessionStorage.removeItem(CHAVE_DO_TOKEN);
  } catch {
    // O token continua em memória.
  }
}

// Lê as claims sem validar a assinatura: só o servidor confia no token; a tela só escolhe menus.
export function lerSessao() {
  const token = lerToken();
  if (!token) return null;
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(atob(base64));
    if (claims.exp * 1000 <= Date.now()) return null;
    return { usuarioId: claims.sub, perfil: claims.role, expiraEm: new Date(claims.exp * 1000) };
  } catch {
    return null;
  }
}

let aoPerderASessao = () => {};

export function quandoPerderASessao(funcao) {
  aoPerderASessao = funcao;
}

export async function chamarApi(metodo, caminho, corpo) {
  const cabecalhos = { Accept: "application/json" };
  const token = lerToken();
  if (token) cabecalhos.Authorization = `Bearer ${token}`;
  if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";

  let resposta;
  try {
    resposta = await fetch(caminho, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch {
    throw new ErroDaApi(0, { mensagem: "Sem conexão com o servidor." });
  }

  const conteudo = resposta.status === 204 ? null : await resposta.json().catch(() => null);
  if (resposta.ok) return conteudo;

  const erro = new ErroDaApi(resposta.status, conteudo, resposta.headers);
  if (resposta.status === 401 && token) {
    guardarToken(null);
    aoPerderASessao(erro);
  }
  throw erro;
}

export function consultaComFiltros(caminho, filtros) {
  const parametros = new URLSearchParams();
  for (const [nome, valor] of Object.entries(filtros)) {
    if (valor !== undefined && valor !== null && valor !== "") parametros.set(nome, valor);
  }
  const texto = parametros.toString();
  return texto ? `${caminho}?${texto}` : caminho;
}
