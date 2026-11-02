// fluency-hooks.js - shim de plugin OpenCode para la suite fluency-4d.
// Generado por tools/multiharness/build_harness.py. NO editar a mano.
//
// Proposito: PUENTEAR (no reescribir) los hooks Python de fluency-4d
// al ciclo de vida de OpenCode. En el evento equivalente a
// UserPromptSubmit de Claude Code, invoca cada hook Python por
// subprocess (uv run --script <ruta_abs>), le pasa el input por stdin
// (JSON, contrato de Claude) y reinyecta el `additionalContext` que
// emite por stdout.
//
// API OpenCode 1.19.1 (verificada): el hook `chat.message` se dispara al
// crear el mensaje del usuario, ANTES de persistirlo y de llamar al
// modelo: input = {sessionID, agent, model, messageID, variant},
// output = {message, parts}. El texto del usuario vive en output.parts.
// - La parte inyectada va con `synthetic: true`: el modelo la recibe,
//   pero la TUI no la muestra/copia/edita como texto del usuario.
// - Su id es ascendente (mismo formato que los ids nativos) y mayor que
//   el de las partes del usuario -> queda DESPUES del prompt.
// - Subagentes (sesion hija de la tool task / agente mode subagent): NO
//   se inyecta nada (los hooks tambien lo saltean por agent_type).
// Ante cualquier fallo el shim degrada a NO-OP: nunca rompe la sesion.

import { spawnSync } from "node:child_process";
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
// OpenCode) si el client del plugin no responde.
const KNOWN_SUBAGENTS = new Set(["advisor", "auditor-de-redaccion", "bug-hunter", "code-reviewer", "compliance-auditor", "critic", "debugger", "explore", "general", "librarian", "risk-assessor", "security-auditor", "validator"]);

// Python en Windows lee stdin con la codepage ANSI (cp1252) salvo que se
// fuerce UTF-8: sin esto los prompts con acentos rompen los keywords.
const HOOK_ENV = { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8" };

// Traduccion minima del texto que emiten los hooks (escritos para Claude
// Code) a los nombres de OpenCode.
const CONTEXT_REWRITES = [
  [/\bsentinel-agents[:]([a-z][a-z-]*)/g, "$1"],
  [/\bExitPlanMode\b/g, "plan_exit"],
];

// --- ids ascendentes (formato OpenCode: prefijo_ + 12 hex de
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

// Invoca un hook Python y devuelve su additionalContext (o '' si no aplica).
function runPythonHook(scriptPath, payload) {
  try {
    const res = spawnSync("uv", ["run", "--script", scriptPath], {
      input: JSON.stringify(payload || {}),
      encoding: "utf8",
      env: HOOK_ENV,
      timeout: 5000,
      windowsHide: true,
    });
    if (res.status !== 0 || !res.stdout) return "";
    const out = JSON.parse(res.stdout);
    const spec = out && out.hookSpecificOutput;
    return (spec && spec.additionalContext) ? String(spec.additionalContext) : "";
  } catch (_e) {
    return ""; // fail-degraded: un hook que falla nunca rompe la sesion.
  }
}

function collectContext(payload) {
  const chunks = [];
  for (const script of USER_PROMPT_HOOKS) {
    let ctx = runPythonHook(script, payload);
    if (!ctx) continue;
    for (const [re, rep] of CONTEXT_REWRITES) ctx = ctx.replace(re, rep);
    chunks.push(ctx);
  }
  return chunks.join("\n\n");
}

function withTimeout(promise, ms) {
  return Promise.race([
    Promise.resolve(promise).catch(() => undefined),
    new Promise((resolve) => setTimeout(() => resolve(undefined), ms)),
  ]);
}

export const FluencyHooks = async ({ client, directory, worktree } = {}) => {
  const subagentBySession = new Map(); // sessionID -> boolean (cache)
  let agentModes = null; // nombre -> mode (cache de client.app.agents)

  async function loadAgentModes() {
    if (agentModes) return agentModes;
    try {
      const r = await withTimeout(client.app.agents(), 3000);
      const list = (r && (r.data || r)) || [];
      if (Array.isArray(list) && list.length) {
        agentModes = {};
        for (const a of list) if (a && a.name) agentModes[a.name] = a.mode;
      }
    } catch (_e) { /* fallback: KNOWN_SUBAGENTS */ }
    return agentModes || {};
  }

  // Subagente = sesion hija (la tool task crea la sesion con parentID) o
  // agente con mode "subagent"; fallback: lista estatica del bundle.
  async function isSubagent(input) {
    const sid = input && input.sessionID;
    if (sid && subagentBySession.has(sid)) return subagentBySession.get(sid);
    const agent = input && input.agent;
    let sub = Boolean(agent && KNOWN_SUBAGENTS.has(agent));
    if (!sub && client && sid) {
      try {
        const r = await withTimeout(client.session.get({ path: { id: sid } }), 3000);
        const s = r && (r.data || r);
        if (s && s.parentID) sub = true;
      } catch (_e) { /* sin dato */ }
    }
    if (!sub && client && agent) {
      const modes = await loadAgentModes();
      if (modes[agent] === "subagent") sub = true;
    }
    if (sid) subagentBySession.set(sid, sub);
    return sub;
  }

  return {
    // chat.message = equivalente a UserPromptSubmit.
    "chat.message": async (input, output) => {
      try {
        if (!output || !Array.isArray(output.parts)) return;
        if (await isSubagent(input)) return; // subagentes: no inyectar
        const parts = output.parts;
        const userText = parts
          .filter((p) => p && p.type === "text" && !p.synthetic && typeof p.text === "string")
          .map((p) => p.text)
          .join("\n");
        const payload = {
          session_id: (input && input.sessionID) || "",
          hook_event_name: "UserPromptSubmit",
          prompt: userText,
          cwd: directory || worktree || process.cwd(),
          permission_mode: (input && input.agent === "plan") ? "plan" : "default",
        };
        const extra = collectContext(payload);
        if (!extra) return;
        const ref = parts.find((p) => p && p.sessionID && p.messageID);
        const messageID = (output.message && output.message.id)
          || (ref && ref.messageID) || (input && input.messageID);
        const sessionID = (input && input.sessionID) || (ref && ref.sessionID);
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

export default FluencyHooks;
