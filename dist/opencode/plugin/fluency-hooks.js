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
// TODO(verificar-API-opencode): confirmar el nombre EXACTO del hook de
// OpenCode 1.17.11 equivalente a UserPromptSubmit y su firma
// (input/output). Hasta verificarlo, el shim degrada a NO-OP seguro:
// nunca rompe la sesion.

import { spawnSync } from "node:child_process";

// Rutas absolutas a los hooks Python de fluency-4d (resueltas al generar).
const USER_PROMPT_HOOKS = [
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\bridge_router.py",
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\plan_calibrator.py",
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\caveman_injector.py",
  "C:\\Users\\samud\\dev\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\suite_playbook.py"
];

// Invoca un hook Python y devuelve su additionalContext (o '' si no aplica).
function runPythonHook(scriptPath, payload) {
  try {
    const res = spawnSync("uv", ["run", "--script", scriptPath], {
      input: JSON.stringify(payload || {}),
      encoding: "utf8",
      timeout: 5000,
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
    const ctx = runPythonHook(script, payload);
    if (ctx) chunks.push(ctx);
  }
    return chunks.join("\n\n");
}

// export: forma de plugin de OpenCode (funcion que recibe el ctx del
// harness y devuelve el mapa de hooks). TODO(verificar-API-opencode).
export const FluencyHooks = async ({ project, client, $ } = {}) => {
  return {
    // TODO(verificar-API-opencode): mapear al evento real. Placeholder
    // conservador: "chat.message" segun la API de plugins de OpenCode.
    "chat.message": async (input, output) => {
      try {
        const payload = {
          prompt: (input && input.prompt) || "",
          cwd: (project && project.worktree) || process.cwd(),
        };
        const extra = collectContext(payload);
        if (extra && output && typeof output === "object") {
          // Reinyeccion best-effort del additionalContext.
          output.additionalContext =
            (output.additionalContext ? output.additionalContext + "\n\n" : "") + extra;
        }
      } catch (_e) {
        // NO-OP seguro.
      }
    },
  };
};

export default FluencyHooks;
