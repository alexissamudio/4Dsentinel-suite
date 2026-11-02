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
const HOOK_TIMEOUT_MS = 5000; // por hook (corren en paralelo)
const API_TIMEOUT_MS = 3000; // consultas a la API de OpenCode
const CACHE_MAX = 500; // prompts recordados por el cache de contexto v2

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

// Invoca un hook Python SIN bloquear el event loop y resuelve con su
// additionalContext ('' si no aplica, falla o vence el timeout).
function runPythonHook(scriptPath, payload) {
  return new Promise((resolve) => {
    let child = null;
    let out = "";
    let done = false;
    let timer = null;
    const finish = (value) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      resolve(value);
    };
    timer = setTimeout(() => {
      try {
        if (child) child.kill();
      } catch (_e) {
        // ya termino
      }
      finish("");
    }, HOOK_TIMEOUT_MS);
    try {
      child = spawn("uv", ["run", "--script", scriptPath], {
        env: HOOK_ENV,
        windowsHide: true,
        stdio: ["pipe", "pipe", "ignore"],
      });
      child.on("error", () => finish(""));
      child.stdout.setEncoding("utf8");
      child.stdout.on("data", (chunk) => {
        out += chunk;
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
  return chunks.join("\n\n");
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
// o agente con mode "subagent"; fallback: lista estatica del bundle. Las dos
// consultas a la API van en paralelo; los modos se cachean una vez.
function makeSubagentDetector(getSession, getAgentModes) {
  const bySession = new Map(); // sessionID -> boolean
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
    let sub = Boolean(agent && KNOWN_SUBAGENTS.has(agent));
    if (!sub) {
      const [session, agentModes] = await Promise.all([
        sessionID ? withTimeout(() => getSession(sessionID), API_TIMEOUT_MS) : undefined,
        agent ? loadModes() : {},
      ]);
      if (session && session.parentID) sub = true;
      if (agent && agentModes && agentModes[agent] === "subagent") sub = true;
    }
    if (sessionID) bySession.set(sessionID, sub);
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
        const sid = input && input.sessionID;
        const agent = input && input.agent;
        if (await isSubagent(sid, agent)) return; // subagentes: no inyectar
        const parts = output.parts;
        const userText = parts
          .filter((p) => p && p.type === "text" && !p.synthetic && typeof p.text === "string")
          .map((p) => p.text)
          .join("\n");
        const cwd = directory || worktree || process.cwd();
        const extra = await collectContext(hookPayload(sid, userText, cwd, agent));
        if (!extra) return;
        const ref = parts.find((p) => p && p.sessionID && p.messageID);
        const messageID = (output.message && output.message.id)
          || (ref && ref.messageID) || (input && input.messageID);
        const sessionID = sid || (ref && ref.sessionID);
        if (!messageID || !sessionID) return; // sin ids reales no se inventan
        output.parts.push({
          id: partIDAfter(parts),
          sessionID,
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
    const dir = (s && ((s.location && s.location.directory) || s.directory)) || process.cwd();
    cwdBySession.set(sessionID, dir);
    return dir;
  }

  function remember(key, promise) {
    pending.set(key, promise);
    promise.then((text) => resolved.set(key, text));
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
    await pending.get(lastKey);
    // Reinserta (de atras hacia adelante) el contexto de CADA prompt del
    // historial, como en v1 donde la parte synthetic queda en su mensaje.
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = msgs[i];
      if (!m || m.role !== "user" || isInjected(m)) continue;
      const text = resolved.get(keyOf(m));
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
