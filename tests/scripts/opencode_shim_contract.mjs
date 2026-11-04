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
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";
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

// =============================================================================
// Regresiones de la prueba de estres (una por fix). Cada caso importa una
// VARIANTE del plugin con sus propios hooks falsos y constantes reducidas.
// =============================================================================
const SRC = readFileSync(pluginPath, "utf8");
const constOf = (name) => Number(eval(new RegExp(`const ${name} = ([^;]+);`).exec(SRC)[1]));
const HOOK_STDOUT_MAX = constOf("HOOK_STDOUT_MAX");
const CONTEXT_MAX = constOf("CONTEXT_MAX");
const MAX_CONCURRENT_HOOKS = constOf("MAX_CONCURRENT_HOOKS");
const HEADER = "# /// script\n# requires-python = \">=3.11\"\n# ///\n";
const py = (s) => JSON.stringify(s); // literal de string valido en Python
const fake = (name, body) => {
  const f = join(cwd, name + ".py");
  writeFileSync(f, HEADER + "import json, os, sys, time\n" + body, "utf8");
  return f;
};
const emit = (expr) => `print(json.dumps({"hookSpecificOutput": {"additionalContext": ${expr}}}))\n`;
let nVariant = 0;
async function variant(hooks, consts = {}) {
  let src = SRC.replace(/const USER_PROMPT_HOOKS = \[[\s\S]*?\n\];/,
    "const USER_PROMPT_HOOKS = " + JSON.stringify(hooks) + ";");
  for (const [k, v] of Object.entries(consts)) {
    src = src.replace(new RegExp(`const ${k} = [^;]+;`), `const ${k} = ${v};`);
  }
  const f = join(cwd, `variant_${++nVariant}.mjs`);
  writeFileSync(f, src, "utf8");
  return import(pathToFileURL(f).href);
}
const ECHO = fake("echo", "d = json.loads(sys.stdin.buffer.read().decode('utf-8'))\n"
  + emit("'E:%s|%s|%s' % (d['session_id'], d['cwd'], d['prompt'])"));
const primaryClient = (getImpl, agents = [{ name: "build", mode: "primary" }]) => ({
  session: { get: getImpl },
  app: { agents: async () => ({ data: agents }) },
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- Fix 1: hook colgado -> se mata el ARBOL (uv + python), Node no queda colgado.
{
  const pidFile = join(cwd, "hang.pid");
  const HANG = fake("hang", `open(${py(pidFile)}, "w").write(str(os.getpid()))\n`
    + "time.sleep(30)\n" + emit("'LATE'"));
  const m = await variant([ECHO, HANG], { HOOK_TIMEOUT_MS: 4000 });
  const v = await m.default.server({ client: primaryClient(async () => ({ data: {} })), directory: cwd });
  const o = v1Output("ses_hang", "colgado");
  const t0 = Date.now();
  await v["chat.message"]({ sessionID: "ses_hang", agent: "build" }, o);
  assert.ok(Date.now() - t0 < 7000, "el timeout del hook no corto");
  assert.equal(o.parts[1].text, `E:ses_hang|${cwd}|colgado`, "el hook sano tambien se perdio");
  assert.ok(existsSync(pidFile), "el hook colgado no llego a arrancar python");
  const pid = Number(readFileSync(pidFile, "utf8"));
  const alive = (p) => {
    try {
      process.kill(p, 0);
    } catch (_e) {
      return false;
    }
    try { // zombie sin reapear (contenedor sin init) = muerto
      return !/\) Z /.test(readFileSync(`/proc/${p}/stat`, "utf8"));
    } catch (_e) {
      return true;
    }
  };
  let dead = false;
  for (let i = 0; i < 50 && !dead; i++) {
    dead = !alive(pid);
    if (!dead) await sleep(100);
  }
  assert.ok(dead, "python del hook colgado sobrevivio al timeout (huerfano, pid " + pid + ")");
}

// --- Fix 2a: stdout de un hook por encima de HOOK_STDOUT_MAX -> ese hook aporta "".
{
  const HUGE = fake("huge", "sys.stdin.read()\n" + emit(`"X" * ${HOOK_STDOUT_MAX * 4}`));
  const m = await variant([ECHO, HUGE]);
  const v = await m.default.server({ client: primaryClient(async () => ({ data: {} })), directory: cwd });
  const o = v1Output("ses_huge", "grande");
  await v["chat.message"]({ sessionID: "ses_huge", agent: "build" }, o);
  assert.equal(o.parts[1].text, `E:ses_huge|${cwd}|grande`, "se inyecto el stdout gigante");
}

// --- Fix 2b: contexto concatenado por encima de CONTEXT_MAX -> truncado con marca.
{
  const each = Math.floor(HOOK_STDOUT_MAX / 2); // cada hook queda bajo su tope
  const bigs = ["big1", "big2", "big3"].map((n) => fake(n, "sys.stdin.read()\n" + emit(`"Y" * ${each}`)));
  assert.ok(3 * each > CONTEXT_MAX);
  const m = await variant(bigs);
  const v = await m.default.server({ client: primaryClient(async () => ({ data: {} })), directory: cwd });
  const o = v1Output("ses_big", "muchos");
  await v["chat.message"]({ sessionID: "ses_big", agent: "build" }, o);
  const t = o.parts[1].text;
  assert.ok(t.length <= CONTEXT_MAX, "contexto sin tope total (" + t.length + ")");
  assert.ok(t.length > CONTEXT_MAX / 2);
  assert.ok(t.endsWith("[fluency-4d: contexto truncado]"), "falta la marca de truncado");
}

// --- Fix 3: session.get indeterminado (error o timeout) NO se cachea como "no hija".
for (const kind of ["error", "timeout"]) {
  const m = await variant([ECHO], { API_TIMEOUT_MS: 300 });
  let flaky = true;
  const v = await m.default.server({
    client: primaryClient(async () => {
      if (flaky && kind === "error") throw new Error("boom");
      if (flaky) await sleep(900);
      return { data: { parentID: "ses_padre" } };
    }),
    directory: cwd,
  });
  const o1 = v1Output("ses_flaky", "uno");
  await v["chat.message"]({ sessionID: "ses_flaky", agent: "build" }, o1);
  assert.equal(o1.parts.length, 2, "dato indeterminado: fail-open (inyecta sin cachear)");
  flaky = false;
  const o2 = v1Output("ses_flaky", "dos");
  await v["chat.message"]({ sessionID: "ses_flaky", agent: "build" }, o2);
  assert.equal(o2.parts.length, 1, `v1 cacheo 'no hija' tras ${kind} e inyecto en la hija`);
}
{ // v2: idem, y el cwd de respaldo (process.cwd()) tampoco se cachea.
  const m = await variant([ECHO], { API_TIMEOUT_MS: 300 });
  let flaky = true;
  let hook = null;
  const sesDir = join(cwd, "dir-de-la-sesion");
  await m.default.setup({
    session: {
      hook: async (_n, fn) => { hook = fn; return { dispose() {} }; },
      get: async ({ sessionID }) => {
        if (flaky) throw new Error("boom");
        return { id: sessionID, location: { directory: sesDir },
          ...(sessionID === "ses_hija" ? { parentID: "ses_padre" } : {}) };
      },
    },
    agent: { list: async () => ({ data: [{ id: "build", mode: "primary" }] }) },
  });
  const a = { sessionID: "ses_v2", agent: "build", system: [], messages: [user("m1", "uno")] };
  await hook(a);
  assert.equal(textOf(a.messages[1]), `E:ses_v2|${process.cwd()}|uno`);
  const h1 = { sessionID: "ses_hija", agent: "build", system: [], messages: [user("h1", "x")] };
  await hook(h1);
  assert.equal(h1.messages.length, 2, "dato indeterminado: fail-open");
  flaky = false;
  const b = { sessionID: "ses_v2", agent: "build", system: [], messages: [user("m2", "dos")] };
  await hook(b);
  assert.equal(textOf(b.messages[1]), `E:ses_v2|${sesDir}|dos`, "v2 cacheo el cwd de respaldo");
  const h2 = { sessionID: "ses_hija", agent: "build", system: [], messages: [user("h2", "y")] };
  await hook(h2);
  assert.equal(h2.messages.length, 1, "v2 cacheo 'no hija' tras un error e inyecto en la hija");
}

// --- Menor: primario llamado como un subagente nativo (`general` mode primary).
{
  const m = await variant([ECHO]);
  const v1g = await m.default.server({
    client: primaryClient(async () => ({ data: {} }), [{ name: "general", mode: "primary" }]),
    directory: cwd,
  });
  const o = v1Output("ses_gen", "hola");
  await v1g["chat.message"]({ sessionID: "ses_gen", agent: "general" }, o);
  assert.equal(o.parts.length, 2, "v1: el primario `general` no recibio contexto");
  let hook = null;
  await m.default.setup({
    session: { hook: async (_n, fn) => { hook = fn; return { dispose() {} }; },
      get: async ({ sessionID }) => ({ id: sessionID, location: { directory: cwd } }) },
    agent: { list: async () => ({ data: [{ id: "general", mode: "primary" }] }) },
  });
  const r = { sessionID: "ses_gen2", agent: "general", system: [], messages: [user("g1", "hola")] };
  await hook(r);
  assert.equal(r.messages.length, 2, "v2: el primario `general` no recibio contexto");
}

// --- Menor: v1 sin input.sessionID -> session_id sale de las partes (no "").
{
  const m = await variant([ECHO]);
  const v = await m.default.server({ client: primaryClient(async () => ({ data: {} })), directory: cwd });
  const o = v1Output("ses_partes", "sin sid");
  await v["chat.message"]({ agent: "build" }, o);
  assert.equal(o.parts[1].text, `E:ses_partes|${cwd}|sin sid`);
}

// --- Menor: v2, un prompt desalojado del cache mientras corria no reaparece
// en el historial (pero su propio paso SI recibe su contexto).
{
  const m = await variant([ECHO], { CACHE_MAX: 1 });
  let hook = null;
  await m.default.setup({
    session: { hook: async (_n, fn) => { hook = fn; return { dispose() {} }; },
      get: async ({ sessionID }) => ({ id: sessionID, location: { directory: cwd } }) },
    agent: { list: async () => ({ data: [{ id: "build", mode: "primary" }] }) },
  });
  const a = { sessionID: "ses_ev_a", agent: "build", system: [], messages: [user("m1", "a1")] };
  const b = { sessionID: "ses_ev_b", agent: "build", system: [], messages: [user("n1", "b1")] };
  await Promise.all([hook(a), hook(b)]);
  assert.equal(a.messages.length, 2, "el prompt desalojado perdio su propio contexto");
  assert.equal(b.messages.length, 2);
  const a2 = { sessionID: "ses_ev_a", agent: "build", system: [], messages: [user("m1", "a1"),
    { id: "r1", role: "assistant", content: [{ type: "text", text: "ok" }], metadata: {} },
    user("m2", "a2")] };
  await hook(a2);
  assert.deepEqual(a2.messages.map((x) => (isInjected(x) ? "ctx" : x.role)),
    ["user", "assistant", "user", "ctx"], "una entrada desalojada reaparecio en `resolved`");
}

// --- Menor: semaforo -> nunca mas de MAX_CONCURRENT_HOOKS hooks vivos a la vez.
{
  const spans = join(cwd, "spans.log");
  const SLOW = fake("slow", "sys.stdin.read()\nt0 = time.time()\ntime.sleep(0.6)\n"
    + `open(${py(spans)}, "a").write("%f %f\\n" % (t0, time.time()))\n` + emit("'S'"));
  const m = await variant([SLOW]);
  const v = await m.default.server({ client: primaryClient(async () => ({ data: {} })), directory: cwd });
  const outs = Array.from({ length: MAX_CONCURRENT_HOOKS + 4 }, (_, i) => v1Output("ses_sem" + i, "p"));
  await Promise.all(outs.map((o, i) => v["chat.message"]({ sessionID: "ses_sem" + i, agent: "build" }, o)));
  assert.ok(outs.every((o) => o.parts.length === 2), "algun hook encolado no corrio");
  const ev = readFileSync(spans, "utf8").trim().split("\n").flatMap((l) => {
    const [s, e] = l.split(" ").map(Number);
    return [[s, 1], [e, -1]];
  }).sort((x, y) => x[0] - y[0] || x[1] - y[1]);
  let cur = 0;
  let peak = 0;
  for (const [, d] of ev) { cur += d; peak = Math.max(peak, cur); }
  assert.ok(peak <= MAX_CONCURRENT_HOOKS, "hooks concurrentes: " + peak);
  assert.ok(peak > 1, "los hooks dejaron de correr en paralelo");
}

console.log("OK contrato v1 + v2 del shim OpenCode");
