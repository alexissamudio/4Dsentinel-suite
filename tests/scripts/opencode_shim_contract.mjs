// Contrato del shim OpenCode (dist/opencode/plugin/fluency-hooks.js) con mocks.
//
// Uso: node opencode_shim_contract.mjs <plugin.mjs> <hooks.log> <cwd>
// El plugin llega con USER_PROMPT_HOOKS reemplazado por hooks falsos (ver
// test_build_harness.py): A duerme y emite "A:<prompt>|<permission_mode>|<cwd>",
// B emite "B:sentinel-agents:critic" (el shim lo reescribe a "B:critic"), C
// sale con codigo 1 (se ignora). Cada corrida de A agrega una linea a hooks.log.
// Ejercita: default {id, server, setup} (v1 + v2), parte synthetic v1, hook
// context v2 (sin persistir, cacheado por mensaje), subagentes, orden de
// chunks, hooks async (el event loop sigue vivo) y dispose.
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { pathToFileURL } from "node:url";

const [pluginPath, hooksLog, cwd] = process.argv.slice(2);
const mod = await import(pathToFileURL(pluginPath).href);
const runsOfA = () => (existsSync(hooksLog)
  ? readFileSync(hooksLog, "utf8").split("\n").filter(Boolean).length
  : 0);
const expected = (prompt, mode, dir) => `A:${prompt}|${mode}|${dir}\n\nB:critic`;

// --- default export dual -----------------------------------------------------
assert.equal(typeof mod.default, "object");
assert.equal(typeof mod.default.id, "string");
assert.ok(mod.default.id.length > 0);
assert.equal(mod.default.server, mod.FluencyHooks);
assert.equal(typeof mod.default.setup, "function");

// --- v1: server -> chat.message -------------------------------------------------
const v1Client = {
  session: {
    get: async ({ path }) => ({ data: path.id === "ses_child" ? { parentID: "ses_1" } : {} }),
  },
  app: {
    agents: async () => ({
      data: [{ name: "build", mode: "primary" }, { name: "explore", mode: "subagent" },
        { name: "custom-sub", mode: "subagent" }],
    }),
  },
};
const v1 = await mod.default.server({ client: v1Client, directory: cwd });
assert.equal(typeof v1["chat.message"], "function");

function v1Output(sessionID, text) {
  const messageID = "msg_" + sessionID;
  return {
    message: { id: messageID },
    parts: [{ id: "prt_000000000001AAAAAAAAAAAAAA", sessionID, messageID, type: "text", text }],
  };
}

let ticks = 0;
const ticker = setInterval(() => { ticks += 1; }, 20);
const out = v1Output("ses_1", "hola facturación");
await v1["chat.message"]({ sessionID: "ses_1", agent: "build", messageID: "msg_ses_1" }, out);
clearInterval(ticker);
assert.ok(ticks >= 3, "los hooks bloquearon el event loop (ticks=" + ticks + ")");
assert.equal(out.parts.length, 2);
const injected = out.parts[1];
assert.equal(injected.synthetic, true);
assert.equal(injected.type, "text");
assert.equal(injected.sessionID, "ses_1");
assert.equal(injected.messageID, "msg_ses_1");
assert.ok(injected.id > out.parts[0].id, "la parte inyectada no queda despues del prompt");
assert.equal(injected.text, expected("hola facturación", "default", cwd));

const plan = v1Output("ses_plan", "planear");
await v1["chat.message"]({ sessionID: "ses_plan", agent: "plan" }, plan);
assert.equal(plan.parts[1].text, expected("planear", "plan", cwd));

for (const [sid, agent] of [["ses_child", "build"], ["ses_x", "explore"], ["ses_y", "custom-sub"]]) {
  const o = v1Output(sid, "hola");
  const before = runsOfA();
  await v1["chat.message"]({ sessionID: sid, agent }, o);
  assert.equal(o.parts.length, 1, "v1 inyecto en el subagente " + sid + "/" + agent);
  assert.equal(runsOfA(), before, "v1 corrio hooks en el subagente " + sid);
}

// --- v2: setup(api) -> api.session.hook("context") -----------------------------
let contextHook = null;
let disposed = 0;
const v2Api = {
  session: {
    hook: async (name, fn) => {
      assert.equal(name, "context");
      contextHook = fn;
      return { dispose: async () => { disposed += 1; } };
    },
    get: async ({ sessionID }) => (sessionID === "ses_sub"
      ? { id: sessionID, parentID: "ses_2", location: { directory: cwd } }
      : { id: sessionID, location: { directory: cwd } }),
    synthetic: async () => { throw new Error("v2 no debe persistir con session.synthetic"); },
  },
  agent: {
    list: async () => ({ data: [{ id: "build", mode: "primary" }, { id: "explore", mode: "subagent" }] }),
  },
};
const dispose = await mod.default.setup(v2Api);
assert.equal(typeof contextHook, "function");
assert.equal(typeof dispose, "function");

const user = (id, text) => ({ id, role: "user", content: [{ type: "text", text }], metadata: {} });
const textOf = (m) => m.content.map((c) => c.text).join("");
const isInjected = (m) => Boolean(m.metadata && m.metadata.fluency4d);

const runs0 = runsOfA();
const step1 = { sessionID: "ses_2", agent: "build", system: [], messages: [user("msg_a", "hola facturación")] };
await contextHook(step1);
assert.equal(step1.messages.length, 2);
assert.equal(step1.messages[1].role, "user");
assert.ok(isInjected(step1.messages[1]));
assert.equal(textOf(step1.messages[1]), expected("hola facturación", "default", cwd));
assert.equal(runsOfA(), runs0 + 1);

// Paso de tool del MISMO prompt: reinyecta desde cache, sin volver a correr hooks.
const step2 = {
  sessionID: "ses_2", agent: "build", system: [],
  messages: [user("msg_a", "hola facturación"),
    { id: "msg_r", role: "assistant", content: [{ type: "tool-call" }], metadata: {} },
    { role: "tool", content: [{ type: "tool-result" }] }],
};
await contextHook(step2);
assert.equal(step2.messages.length, 4);
assert.ok(isInjected(step2.messages[1]), "el contexto no quedo pegado al prompt");
assert.equal(step2.messages[2].role, "assistant");
assert.equal(runsOfA(), runs0 + 1, "los hooks corrieron de nuevo en un paso de tool");

// Segundo prompt: corre hooks una vez y conserva el contexto del primero.
const step3 = {
  sessionID: "ses_2", agent: "build", system: [],
  messages: [user("msg_a", "hola facturación"),
    { id: "msg_r", role: "assistant", content: [{ type: "text", text: "ok" }], metadata: {} },
    user("msg_b", "otra cosa")],
};
await contextHook(step3);
assert.deepEqual(step3.messages.map((m) => (isInjected(m) ? "ctx" : m.role)),
  ["user", "ctx", "assistant", "user", "ctx"]);
assert.equal(textOf(step3.messages[4]), expected("otra cosa", "default", cwd));
assert.equal(runsOfA(), runs0 + 2);

// Subagentes (sesion hija o agente mode subagent): ni hooks ni inyeccion.
for (const [sid, agent] of [["ses_sub", "build"], ["ses_3", "explore"]]) {
  const r = { sessionID: sid, agent, system: [], messages: [user("msg_s" + sid, "hola facturación")] };
  const before = runsOfA();
  await contextHook(r);
  assert.equal(r.messages.length, 1, "v2 inyecto en el subagente " + sid + "/" + agent);
  assert.equal(runsOfA(), before);
}

await dispose();
assert.equal(disposed, 1);
console.log("OK contrato v1 + v2 del shim OpenCode");
