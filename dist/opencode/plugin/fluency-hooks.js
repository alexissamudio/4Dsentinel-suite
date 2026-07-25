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
// API OpenCode 1.17.11 (verificada): el hook `chat.message` se dispara
// cuando el usuario envia un mensaje, ANTES de que el modelo lo procese.
// El texto del usuario vive en output.parts (partes type:text), NO en
// input.prompt; la inyeccion de contexto es por output.parts.push(...).
// Ante cualquier fallo el shim degrada a NO-OP: nunca rompe la sesion.

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

// export: forma de plugin de OpenCode (funcion async que recibe el ctx
// del harness y devuelve el mapa de hooks).
export const FluencyHooks = async ({ project, client, $ } = {}) => {
  return {
    // chat.message = equivalente a UserPromptSubmit (dispara al enviar el
    // mensaje del usuario, antes del modelo).
    "chat.message": async (input, output) => {
      try {
        // El texto del usuario esta en output.parts (partes type:text),
        // NO en input.prompt.
        const parts = (output && Array.isArray(output.parts)) ? output.parts : [];
        const userText = parts
          .filter((p) => p && p.type === "text" && typeof p.text === "string")
          .map((p) => p.text)
          .join("\n");
        const payload = {
          prompt: userText,
          cwd: (project && project.worktree) || process.cwd(),
        };
        const extra = collectContext(payload);
        // Inyeccion: se MUTA output.parts empujando una parte de texto
        // (output.additionalContext no existe en la API de OpenCode).
        if (extra && output && Array.isArray(output.parts)) {
          output.parts.push({ type: "text", text: extra });
        }
      } catch (_e) {
        // NO-OP seguro.
      }
    },
  };
};

export default FluencyHooks;
