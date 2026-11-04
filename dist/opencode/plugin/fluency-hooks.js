// fluency-hooks.js - shim de plugin OpenCode para la suite fluency-4d.
// Generado por tools/multiharness/build_harness.py. NO editar a mano.
//
// Proposito: PUENTEAR (no reescribir) los hooks Python de fluency-4d al ciclo
// de vida de OpenCode. En el equivalente a UserPromptSubmit de Claude Code
// invoca cada hook Python por subprocess (uv run --script <ruta_abs>), le pasa
// el input por stdin (JSON, contrato de Claude) y reinyecta el
// `additionalContext` que emite por stdout.
//
// UN archivo, DOS contratos de plugin (verificados en runtime real):
// - OpenCode 1.19.x (v1): lee `default.server` (fn) y usa el hook
//   `chat.message`, que corre al crear el mensaje del usuario ANTES de
//   persistirlo: input = {sessionID, agent, model, messageID, variant},
//   output = {message, parts}. La parte inyectada va con `synthetic: true` (el
//   modelo la ve; la TUI no la muestra como texto del usuario) y con id
//   ascendente mayor que el de las partes del usuario -> queda DESPUES del
//   prompt. Si `default` es un objeto, los exports nombrados se ignoran.
// - OpenCode 2.2.5 (v2): valida `default` contra {id, setup: fn} y llama
//   setup(api). No existe `chat.message`: se usa api.session.hook("context"),
//   que corre en CADA llamada al modelo (tambien en cada paso de tools) con
//   {sessionID, agent, model, system, messages, tools}. Se inserta un mensaje
//   user SIN persistir (no api.session.synthetic) justo despues del mensaje
//   del usuario; el resultado de los hooks se cachea por id de ese mensaje, asi
//   los hooks corren una vez por prompt y no en cada paso de tool.
// - Subagentes (sesion hija con parentID / agente mode subagent): NO se
//   inyecta nada (los hooks tambien lo saltean por agent_type).
// Los hooks corren en paralelo y sin bloquear el event loop (spawn async).
// Ante cualquier fallo el shim degrada a NO-OP: nunca rompe la sesion.

import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";

// Rutas absolutas a los hooks Python de fluency-4d (resueltas al generar).
const USER_PROMPT_HOOKS = [
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\bridge_router.py",
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\plan_calibrator.py",
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\caveman_injector.py",
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\adhd_injector.py",
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\suite_playbook.py"
];

// Fallback de deteccion de subagentes (agentes del bundle + nativos de
// OpenCode) si la API del plugin no responde.
const KNOWN_SUBAGENTS = new Set(["advisor", "auditor-de-redaccion", "bug-hunter", "code-reviewer", "compliance-auditor", "critic", "debugger", "explore", "general", "librarian", "risk-assessor", "security-auditor", "validator"]);

// Python en Windows lee stdin con la codepage ANSI (cp1252) salvo que se
// fuerce UTF-8: sin esto los prompts con acentos rompen los keywords.
const HOOK_ENV = { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8" };
// Por hook (corren en paralelo): el mayor `timeout` de UserPromptSubmit en
// fluency-4d/hooks/hooks.json, el mismo presupuesto que Claude Code y Codex.
const HOOK_TIMEOUT_MS = 15000;
const API_TIMEOUT_MS = 3000; // consultas a la API de OpenCode
const CACHE_MAX = 500; // entradas por cache (prompts v2, sesiones, cwd)
// Topes de tamano (en caracteres JS). Los hooks reales emiten ~1-2 KB por
// prompt; los topes solo frenan un hook roto o malicioso que vuelque MB al
// contexto (en v2 se reinyecta en cada paso de tool):
// - HOOK_STDOUT_MAX: stdout acumulado por hook (JSON incluido). Si se pasa, se
//   mata el arbol del hook y ese hook aporta "".
// - CONTEXT_MAX: contexto concatenado de todos los hooks; se trunca con marca.
const HOOK_STDOUT_MAX = 64 * 1024;
const CONTEXT_MAX = 32 * 1024;
const TRUNCATED_MARK = "\n\n[fluency-4d: contexto truncado]";
// Hooks (procesos uv+python) vivos a la vez entre todos los prompts.
const MAX_CONCURRENT_HOOKS = 8;

// Traduccion minima del texto que emiten los hooks (escritos para Claude
// Code) a los nombres de OpenCode.
const CONTEXT_REWRITES = [
  [/\bsentinel-agents[:]([a-z][a-z-]*)/g, "$1"],
  [/\bExitPlanMode\b/g, "plan_exit"],
];

// --- ids ascendentes v1 (formato OpenCode: prefijo_ + 12 hex de
// (ms*0x1000+contador) truncado a 48 bits + 14 base62) ---
const B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
const MASK48 = (1n << 48n) - 1n;
function idTime(id) {
  const m = /^[a-z]+_([0-9a-f]{12})/.exec(String(id || ""));
  return m ? BigInt("0x" + m[1]) : -1n;
}
function partIDAfter(parts) {
  // Ultimo slot del ms actual, o el siguiente a la mayor parte existente.
  let t = (BigInt(Date.now()) * 0x1000n + 0xfffn) & MASK48;
  for (const p of parts) {
    const v = idTime(p && p.id);
    if (v >= t) t = (v + 1n) & MASK48;
  }
  const rnd = Array.from(randomBytes(14), (b) => B62[b % 62]).join("");
  return "prt_" + t.toString(16).padStart(12, "0") + rnd;
}

// Semaforo de spawns: como mucho MAX_CONCURRENT_HOOKS hooks vivos a la vez.
let activeHooks = 0;
const hookQueue = [];
function acquireHookSlot() {
  if (activeHooks < MAX_CONCURRENT_HOOKS) {
    activeHooks += 1;
    return Promise.resolve();
  }
  return new Promise((resolve) => hookQueue.push(resolve));
}
function releaseHookSlot() {
  const next = hookQueue.shift();
  if (next) next(); // el slot pasa directo al siguiente
  else activeHooks -= 1;
}

const IS_WIN = process.platform === "win32";

// Mata el ARBOL del hook. child.kill() solo mata uv: python queda huerfano,
// retiene el pipe de stdout y Node no termina hasta que sale. En Windows,
// taskkill /T /F; en POSIX el hook arranca en su propio grupo (detached) y se
// mata el grupo entero. Nunca lanza.
function killTree(child) {
  if (!child || !child.pid || child.exitCode !== null || child.signalCode !== null) return;
  try {
    if (IS_WIN) {
      const k = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
        windowsHide: true,
        stdio: "ignore",
      });
      k.on("error", () => {
        try {
          child.kill();
        } catch (_e) {
          // ya termino
        }
      });
    } else {
      process.kill(-child.pid, "SIGKILL");
    }
  } catch (_e) {
    try {
      child.kill("SIGKILL");
    } catch (_e2) {
      // ya termino
    }
  }
}

// Invoca un hook Python SIN bloquear el event loop y resuelve con su
// additionalContext ('' si no aplica, falla, vence el timeout o se pasa de
// HOOK_STDOUT_MAX).
async function runPythonHook(scriptPath, payload) {
  await acquireHookSlot();
  return new Promise((resolve) => {
    let child = null;
    let out = "";
    let done = false;
    let timer = null;
    const finish = (value) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      releaseHookSlot();
      resolve(value);
    };
    const abort = () => {
      killTree(child);
      try {
        // Suelta los pipes ya: Node no espera al arbol para seguir/terminar.
        if (child) {
          child.stdout.destroy();
          child.stdin.destroy();
        }
      } catch (_e) {
        // sin pipes
      }
      finish("");
    };
    timer = setTimeout(abort, HOOK_TIMEOUT_MS);
    try {
      child = spawn("uv", ["run", "--script", scriptPath], {
        env: HOOK_ENV,
        windowsHide: true,
        detached: !IS_WIN, // POSIX: grupo propio para matar el arbol
        stdio: ["pipe", "pipe", "ignore"],
      });
      child.on("error", () => finish(""));
      child.stdout.setEncoding("utf8");
      child.stdout.on("data", (chunk) => {
        if (done) return;
        out += chunk;
        if (out.length > HOOK_STDOUT_MAX) abort();
      });
      child.on("close", (code) => {
        if (code !== 0 || !out) return finish("");
        try {
          const spec = JSON.parse(out).hookSpecificOutput;
          finish(spec && spec.additionalContext ? String(spec.additionalContext) : "");
        } catch (_e) {
          finish("");
        }
      });
      child.stdin.on("error", () => {}); // el hook cerro stdin: sin dato
      child.stdin.end(JSON.stringify(payload || {}));
    } catch (_e) {
      finish(""); // fail-degraded: un hook que falla nunca rompe la sesion.
    }
  });
}

// Corre los hooks en paralelo; los chunks conservan el orden de USER_PROMPT_HOOKS.
async function collectContext(payload) {
  const results = await Promise.all(USER_PROMPT_HOOKS.map((s) => runPythonHook(s, payload)));
  const chunks = [];
  for (let ctx of results) {
    if (!ctx) continue;
    for (const [re, rep] of CONTEXT_REWRITES) ctx = ctx.replace(re, rep);
    chunks.push(ctx);
  }
  return capContext(chunks.join("\n\n"));
}

// Trunca a CONTEXT_MAX (marca incluida) sin partir un par surrogate.
function capContext(text) {
  if (text.length <= CONTEXT_MAX) return text;
  let cut = CONTEXT_MAX - TRUNCATED_MARK.length;
  const c = text.charCodeAt(cut - 1);
  if (c >= 0xd800 && c <= 0xdbff) cut -= 1;
  return text.slice(0, cut) + TRUNCATED_MARK;
}

// Map acotado: al pasar de CACHE_MAX se descarta la entrada mas vieja.
function boundedSet(map, key, value) {
  map.delete(key); // re-insercion = mas reciente
  map.set(key, value);
  while (map.size > CACHE_MAX) map.delete(map.keys().next().value);
}

// Resuelve con fn() o con undefined si falla o tarda mas de ms. El timer se
// limpia apenas hay resultado (no quedan timers vivos por llamada).
function withTimeout(fn, ms) {
  let timer = null;
  const call = new Promise((resolve) => resolve(fn())).catch(() => undefined);
  const expire = new Promise((resolve) => {
    timer = setTimeout(() => resolve(undefined), ms);
  });
  return Promise.race([call, expire]).finally(() => clearTimeout(timer));
}

function unwrap(r) {
  return r && typeof r === "object" && "data" in r ? r.data : r;
}

// Subagente = sesion hija (la tool task/subagent crea la sesion con parentID)
// o agente con mode "subagent". El mode de la API manda; la lista estatica del
// bundle es solo el fallback si la API no lo da (asi un primario llamado como
// un subagente nativo, p. ej. `general` con mode primary, sigue recibiendo
// contexto). Las dos consultas van en paralelo; los modos se cachean una vez.
// Solo se cachea por sesion un resultado DETERMINADO: si session.get vence o
// falla, no se sabe si es hija -> se responde sin cachear y se reintenta en la
// proxima llamada (antes quedaba `false` para siempre e inyectaba en la hija).
function makeSubagentDetector(getSession, getAgentModes) {
  const bySession = new Map(); // sessionID -> boolean (solo determinados)
  let modes = null; // Promise<{agente: mode}>
  const loadModes = () => {
    if (!modes) {
      modes = withTimeout(getAgentModes, API_TIMEOUT_MS).then((m) => {
        if (!m || !Object.keys(m).length) modes = null; // reintentar luego
        return m || {};
      });
    }
    return modes;
  };
  return async function isSubagent(sessionID, agent) {
    if (sessionID && bySession.has(sessionID)) return bySession.get(sessionID);
    const [session, agentModes] = await Promise.all([
      sessionID ? withTimeout(() => getSession(sessionID), API_TIMEOUT_MS) : undefined,
      agent ? loadModes() : {},
    ]);
    const sessionKnown = Boolean(session && typeof session === "object");
    const mode = agent && agentModes ? agentModes[agent] : undefined;
    let sub;
    let known;
    if (sessionKnown && session.parentID) {
      sub = true;
      known = true;
    } else if (mode) {
      sub = mode === "subagent";
      known = sub || sessionKnown;
    } else if (agent && KNOWN_SUBAGENTS.has(agent)) {
      sub = true;
      known = true; // match en la lista del bundle
    } else {
      sub = false;
      known = sessionKnown;
    }
    if (sessionID && known) boundedSet(bySession, sessionID, sub);
    return sub;
  };
}

function modesFrom(list, keys) {
  const out = {};
  if (!Array.isArray(list)) return out;
  for (const a of list) {
    if (!a) continue;
    for (const k of keys) if (a[k]) out[a[k]] = a.mode;
  }
  return out;
}

function hookPayload(sessionID, prompt, cwd, agent) {
  return {
    session_id: sessionID || "",
    hook_event_name: "UserPromptSubmit",
    prompt,
    cwd,
    permission_mode: agent === "plan" ? "plan" : "default",
  };
}

// --- v1: default.server -> chat.message (parte synthetic persistida) -------
export const FluencyHooks = async ({ client, directory, worktree } = {}) => {
  const isSubagent = makeSubagentDetector(
    async (id) => unwrap(await client.session.get({ path: { id } })),
    async () => modesFrom(unwrap(await client.app.agents()), ["name"]),
  );

  return {
    // chat.message = equivalente a UserPromptSubmit.
    "chat.message": async (input, output) => {
      try {
        if (!output || !Array.isArray(output.parts)) return;
        const parts = output.parts;
        // Ids ANTES del payload: sin input.sessionID se toma el de las partes
        // (si no, el hook recibia session_id "" y compartia estado de dedup).
        const ref = parts.find((p) => p && p.sessionID && p.messageID);
        const sid = (input && input.sessionID) || (ref && ref.sessionID);
        const messageID = (output.message && output.message.id)
          || (ref && ref.messageID) || (input && input.messageID);
        if (!messageID || !sid) return; // sin ids reales no se inventan
        const agent = input && input.agent;
        if (await isSubagent(sid, agent)) return; // subagentes: no inyectar
        const userText = parts
          .filter((p) => p && p.type === "text" && !p.synthetic && typeof p.text === "string")
          .map((p) => p.text)
          .join("\n");
        const cwd = directory || worktree || process.cwd();
        const extra = await collectContext(hookPayload(sid, userText, cwd, agent));
        if (!extra) return;
        output.parts.push({
          id: partIDAfter(parts),
          sessionID: sid,
          messageID,
          type: "text",
          synthetic: true,
          text: extra,
        });
      } catch (_e) {
        // NO-OP seguro.
      }
    },
  };
};

// --- v2: default.setup -> api.session.hook("context") (sin persistir) --------
const INJECTED = "fluency4d"; // marca en metadata del mensaje inyectado

function messageText(m) {
  const content = m && Array.isArray(m.content) ? m.content : [];
  return content
    .filter((c) => c && c.type === "text" && typeof c.text === "string")
    .map((c) => c.text)
    .join("\n");
}

function isInjected(m) {
  return Boolean(m && m.metadata && m.metadata[INJECTED]);
}

export async function setupV2(api) {
  const isSubagent = makeSubagentDetector(
    async (sessionID) => unwrap(await api.session.get({ sessionID })),
    async () => modesFrom(unwrap(await api.agent.list()), ["id", "name"]),
  );
  const pending = new Map(); // "sesion:mensaje" -> Promise<string>
  const resolved = new Map(); // "sesion:mensaje" -> string (para el historial)
  const cwdBySession = new Map();

  async function sessionCwd(sessionID) {
    if (cwdBySession.has(sessionID)) return cwdBySession.get(sessionID);
    const s = await withTimeout(
      async () => unwrap(await api.session.get({ sessionID })),
      API_TIMEOUT_MS,
    );
    const dir = s && ((s.location && s.location.directory) || s.directory);
    if (!dir) return process.cwd(); // respaldo NO cacheado: se reintenta
    boundedSet(cwdBySession, sessionID, dir);
    return dir;
  }

  function remember(key, promise) {
    pending.set(key, promise);
    // Solo si la clave sigue viva: una entrada desalojada mientras corria no
    // debe reaparecer en `resolved` (fuga + contexto viejo en el historial).
    promise.then((text) => {
      if (pending.get(key) === promise) resolved.set(key, text);
    });
    while (pending.size > CACHE_MAX) {
      const oldest = pending.keys().next().value;
      pending.delete(oldest);
      resolved.delete(oldest);
    }
  }

  async function onContext(r) {
    if (!r || !Array.isArray(r.messages) || !r.sessionID) return;
    if (await isSubagent(r.sessionID, r.agent)) return; // subagentes: no inyectar
    const msgs = r.messages;
    // TODO(estres): un mensaje user AJENO al final (recordatorio de plan mode u
    // otro plugin, despues de un paso de tool) se toma como "el prompt": corre
    // los hooks con ese texto y no con el del usuario. No se filtra todavia
    // porque la forma de esos mensajes en v2 no esta validada en runtime real.
    let last = -1;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i] && msgs[i].role === "user" && !isInjected(msgs[i])) {
        last = i;
        break;
      }
    }
    if (last === -1) return;
    const keyOf = (m) => r.sessionID + ":" + (m.id || messageText(m));
    const lastKey = keyOf(msgs[last]);
    if (!pending.has(lastKey)) {
      const prompt = messageText(msgs[last]);
      const agent = r.agent;
      remember(
        lastKey,
        sessionCwd(r.sessionID)
          .then((cwd) => collectContext(hookPayload(r.sessionID, prompt, cwd, agent)))
          .catch(() => ""),
      );
    }
    // El prompt actual usa su propio resultado (aunque lo hayan desalojado
    // del cache mientras corria); el historial, lo que quede en `resolved`.
    const lastText = await pending.get(lastKey);
    // Reinserta (de atras hacia adelante) el contexto de CADA prompt del
    // historial, como en v1 donde la parte synthetic queda en su mensaje.
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = msgs[i];
      if (!m || m.role !== "user" || isInjected(m)) continue;
      const text = i === last ? lastText : resolved.get(keyOf(m));
      if (!text || isInjected(msgs[i + 1])) continue;
      msgs.splice(i + 1, 0, {
        role: "user",
        content: [{ type: "text", text }],
        metadata: { [INJECTED]: true },
      });
    }
  }

  const handle = await api.session.hook("context", async (r) => {
    try {
      await onContext(r);
    } catch (_e) {
      // NO-OP seguro.
    }
  });
  return () => {
    try {
      if (handle && handle.dispose) return handle.dispose();
    } catch (_e) {
      // ya cerrado
    }
  };
}

// v1 (1.19.x) lee `server`; v2 (2.x) exige `id` y lee `setup`.
export default {
  id: "4dsentinel.fluency-hooks",
  server: FluencyHooks,
  setup: setupV2,
};
