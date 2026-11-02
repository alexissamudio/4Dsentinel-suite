// Testeo "insane" del fix: `mode` sin argumento muestra THEME (el tema efectivo
// del render), nunca un tema invalido del archivo.
//
// Dos arneses:
//  - inProc: compila statusline.js UNA vez (vm.compileFunction) y lo ejecuta con
//    process/os/console/setTimeout falsos. Sirve para fuzzear miles de casos
//    rapido. HOME apunta a un dir temporal (os.homedir falso); nunca toca el
//    ~/.claude real.
//  - sub: subprocess real con HOME/USERPROFILE/TMP/TEMP aislados (y a diferencia
//    de helpers.run, deja pasar STATUSLINE_THEME), para confirmar que el arnes no
//    miente y para lo que solo se ve de verdad (argv, directorio, stack traces).
// Fuzz con LCG de semilla fija -> reproducible: cada falla imprime seed/iter/valor.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');
const { SCRIPT } = require('./helpers');

// Copia de las paletas de statusline.js (el test 'sync' verifica que coincidan).
const PALETTES = {
  'tokyo-night': { dim: '565f89', label: '9aa5ce', text: 'c0caf5', model: '7aa2f7', accent: 'bb9af7', git: 'ff9e64', ok: '9ece6a', warn: 'e0af68', bad: 'f7768e' },
  catppuccin: { dim: '6c7086', label: 'a6adc8', text: 'cdd6f4', model: '89b4fa', accent: 'cba6f7', git: 'fab387', ok: 'a6e3a1', warn: 'f9e2af', bad: 'f38ba8' },
  nord: { dim: '4c566a', label: 'd8dee9', text: 'eceff4', model: '88c0d0', accent: 'b48ead', git: 'd08770', ok: 'a3be8c', warn: 'ebcb8b', bad: 'bf616a' },
  gruvbox: { dim: '928374', label: 'bdae93', text: 'ebdbb2', model: '83a598', accent: 'd3869b', git: 'fe8019', ok: 'b8bb26', warn: 'fabd2f', bad: 'fb4934' },
  templado: { dim: '8c877d', label: 'a8a49a', text: 'e8e6dc', model: 'e8e6dc', accent: 'e8e6dc', git: 'a8a49a', ok: '8aa68a', warn: 'b8a070', bad: 'bd8282', rule: '4a4640', dot: 'd97757' },
};
const NAMES = Object.keys(PALETTES);
const valid = (t) => typeof t === 'string' && Object.hasOwn(PALETTES, t);
const expectedTheme = (fileTheme, envTheme) => (valid(fileTheme) ? fileTheme : valid(envTheme) ? envTheme : 'templado');

// Input rico para que el render pinte muchos colores distintos.
const nowSec = () => Math.floor(Date.now() / 1000);
const RICH = JSON.stringify({
  model: { display_name: 'Opus' },
  context_window: { context_window_size: 200000, current_usage: { input_tokens: 90000, cache_read_input_tokens: 40000 }, used_percentage: 65 },
  cost: { total_cost_usd: 1.23 },
  prompt_cache: { warm: true, hit_ratio: 0.75, expires_at: nowSec() + 600 },
  rate_limits: { five_hour: { used_percentage: 92, resets_at: nowSec() + 3600 }, seven_day: { used_percentage: 20, resets_at: nowSec() + 86400 } },
});

const STACK_RE = /\n\s+at\s.+[:(]\d+:\d+|^\s*at\s.+\.js:\d+|(Type|Reference|Syntax|Range)Error:|node:internal/m;
const colorsOf = (s) => {
  const set = new Set();
  for (const m of s.matchAll(/\x1b\[38;2;(\d+);(\d+);(\d+)m/g)) {
    set.add([m[1], m[2], m[3]].map((n) => Number(n).toString(16).padStart(2, '0')).join(''));
  }
  return set;
};
// Temas cuya paleta contiene TODOS los colores del render.
const themesMatching = (colors) => NAMES.filter((n) => [...colors].every((c) => Object.values(PALETTES[n]).includes(c)));
const shownTheme = (out) => {
  const m = /tema ([^)]*)\)/.exec(out);
  return m ? m[1] : undefined;
};

// --- LCG reproducible (Numerical Recipes) ---
function lcg(seed) {
  let s = seed >>> 0;
  const next = () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296;
  const int = (n) => Math.floor(next() * n);
  const pick = (a) => a[int(a.length)];
  return { next, int, pick };
}
const PROTO_KEYS = ['__proto__', 'constructor', 'toString', 'hasOwnProperty', 'valueOf', '__defineGetter__',
  '__lookupGetter__', 'isPrototypeOf', 'propertyIsEnumerable', 'toLocaleString', 'prototype'];
const WEIRD = ['Templado', 'NORD', 'Nord', ' nord ', 'nord ', ' nord', 'nord\n', 'nord\r\n', '\tgruvbox', 'tokyo night',
  'tokyo_night', 'Tokyo-Night', 'tokyo-night​', '​nord', 'nоrd' /* o cirilica */, 'ｎｏｒｄ', 'nord\u0000',
  'nord\x1b[31m', '\x1b]0;x\x07', 'catppucciń', 'gruvbox﻿', '﻿nord', '', ' ', 'undefined', 'null',
  'true', '0', 'templado.', 'templado/..', '../templado', 'THEMES', 'palette', 'rule', 'dot', 'text', 'simple',
  'experto', 'silencio', 'avisos', 'mode'];
const CHARS = ['a', 'n', 'o', 'r', 'd', '-', '_', ' ', '\t', '\n', '\r', '\x00', '\x07', '\x1b', '\x7f', '\u0085',
  'é', '​', '﻿', ' ', '😀', '\ud800', 'N', 'T', '"', '\\', '{', '}', '%', '$'];
function randString(r) {
  const k = r.int(5);
  if (k === 0) return r.pick(PROTO_KEYS);
  if (k === 1) return r.pick(WEIRD);
  if (k === 2) { // mutacion de un nombre valido
    let s = r.pick(NAMES);
    const op = r.int(5);
    if (op === 0) s = s.toUpperCase();
    else if (op === 1) s = r.pick(CHARS) + s;
    else if (op === 2) s = s + r.pick(CHARS);
    else if (op === 3) { const i = r.int(s.length + 1); s = s.slice(0, i) + r.pick(CHARS) + s.slice(i); }
    else s = s.slice(0, Math.max(0, s.length - 1 - r.int(2)));
    return s;
  }
  if (k === 3) return r.pick(NAMES); // valido de verdad
  let s = '';
  for (let i = r.int(12); i > 0; i--) s += r.pick(CHARS);
  return s;
}
function randValue(r, depth = 0) {
  const k = r.int(depth > 1 ? 7 : 10);
  if (k <= 3) return randString(r);
  if (k === 4) return null;
  if (k === 5) return r.pick([0, -1, 1.5, 1e308, -0, 42]);
  if (k === 6) return r.next() < 0.5;
  if (k === 7) return [randValue(r, depth + 1), r.pick(NAMES)];
  if (k === 8) return { theme: r.pick(NAMES), [r.pick(PROTO_KEYS)]: randValue(r, depth + 1) };
  return [r.pick(NAMES)];
}
// Version para env/argv reales: sin NUL (spawn lo rechaza) ni surrogates sueltos.
const forSpawn = (s) => s.replace(/\x00/g, '').replace(/[\ud800-\udfff]/g, '?');

// --- Arnes in-process ---
const SOURCE = fs.readFileSync(SCRIPT, 'utf8').replace(/^#!.*/, '');
const COMPILED = vm.compileFunction(SOURCE,
  ['require', 'module', 'exports', 'process', 'console', 'setTimeout', '__filename', '__dirname'],
  { filename: SCRIPT });
class Exit { constructor(code) { this.code = code; } }

function inProc({ home, args = [], env = {}, input = RICH }) {
  let stdout = '';
  let stderr = '';
  const handlers = {};
  const fakeOs = { ...os, homedir: () => home };
  const fakeReq = (m) => (m === 'os' ? fakeOs : require(m));
  const fakeProc = {
    argv: [process.execPath, SCRIPT, ...args],
    env: { ...env },
    pid: process.pid,
    platform: process.platform,
    cwd: () => home,
    exit: (c) => { throw new Exit(c === undefined ? 0 : c); },
    stdout: { write: (s, cb) => { stdout += s; if (cb) cb(); return true; } },
    stderr: { write: (s) => { stderr += s; return true; } },
    stdin: { setEncoding() {}, on(ev, cb) { handlers[ev] = cb; } },
  };
  const fakeConsole = {
    log: (...a) => { stdout += a.join(' ') + '\n'; },
    error: (...a) => { stderr += a.join(' ') + '\n'; },
    warn: (...a) => { stderr += a.join(' ') + '\n'; },
  };
  const fakeTimeout = () => ({ unref() {} });
  let status = null;
  let crash = null;
  try {
    COMPILED(fakeReq, { exports: {} }, {}, fakeProc, fakeConsole, fakeTimeout, SCRIPT, path.dirname(SCRIPT));
    if (handlers.data) handlers.data(input);
    if (handlers.end) handlers.end();
  } catch (e) {
    if (e instanceof Exit) status = e.code;
    else crash = e;
  }
  return { stdout, stderr, status, crash };
}

// --- Arnes subprocess (HOME/USERPROFILE/TMP/TEMP aislados) ---
function tempHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'fluency4d-insane-'));
}
function stateFile(home) {
  const dir = path.join(home, '.claude', 'fluency4d');
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, 'statusline.json');
}
function sub({ home, args = [], env = {}, input = RICH }) {
  const tmp = path.join(home, 'tmp');
  fs.mkdirSync(tmp, { recursive: true });
  const childEnv = { ...process.env, HOME: home, USERPROFILE: home, TMP: tmp, TEMP: tmp, TMPDIR: tmp };
  delete childEnv.STATUSLINE_THEME;
  delete childEnv.STATUSLINE_MODE;
  delete childEnv.STATUSLINE_CUT_TOKENS;
  Object.assign(childEnv, env);
  const r = spawnSync(process.execPath, [SCRIPT, ...args], { input, encoding: 'utf8', env: childEnv, timeout: 20000 });
  return { stdout: r.stdout || '', stderr: r.stderr || '', status: r.status, error: r.error };
}

// Chequea la propiedad central en un HOME ya preparado.
function checkProperty(runner, home, env, expected, ctx) {
  const m = runner({ home, args: ['mode'], env });
  assert.ok(!m.crash, `${ctx}: crash en mode: ${m.crash && m.crash.stack}`);
  assert.strictEqual(m.status, 0, `${ctx}: mode sin arg salio ${m.status}`);
  assert.doesNotMatch(m.stdout, STACK_RE, `${ctx}: stack en stdout de mode`);
  const shown = shownTheme(m.stdout);
  assert.ok(valid(shown), `${ctx}: mode mostro tema invalido ${JSON.stringify(shown)} -> ${JSON.stringify(m.stdout)}`);
  assert.strictEqual(shown, expected, `${ctx}: mode mostro ${shown}, esperado ${expected}`);
  const rr = runner({ home, args: [], env });
  assert.ok(!rr.crash, `${ctx}: crash en render: ${rr.crash && rr.crash.stack}`);
  assert.doesNotMatch(rr.stdout, STACK_RE, `${ctx}: stack en stdout del render`);
  const colors = colorsOf(rr.stdout);
  assert.ok(colors.size >= 3, `${ctx}: render con pocos colores (${colors.size})`);
  const matching = themesMatching(colors);
  assert.deepStrictEqual(matching, [shown], `${ctx}: render pinta con ${JSON.stringify(matching)} pero mode dice ${shown}`);
}

// ---------------------------------------------------------------------------

test('sync: las paletas copiadas coinciden con THEMES de statusline.js', () => {
  for (const [name, pal] of Object.entries(PALETTES)) {
    const key = /^[a-z]+$/.test(name) ? name : `'${name}'`;
    const line = SOURCE.split('\n').find((l) => l.trimStart().startsWith(`${key}:`));
    assert.ok(line, `no encontre ${name} en THEMES`);
    for (const [k, v] of Object.entries(pal)) assert.match(line, new RegExp(`\\b${k}: '${v}'`), `${name}.${k}`);
  }
});

test('sanity: el arnes in-process coincide con el subprocess real', () => {
  const r = lcg(7);
  for (let i = 0; i < 25; i++) {
    const home = tempHome();
    const fileTheme = i < 5 ? NAMES[i] : randValue(r);
    const envTheme = forSpawn(r.next() < 0.5 ? r.pick(NAMES) : randString(r));
    fs.writeFileSync(stateFile(home), JSON.stringify({ theme: fileTheme }));
    const env = { STATUSLINE_THEME: envTheme };
    const a = inProc({ home, args: ['mode'], env });
    const b = sub({ home, args: ['mode'], env });
    assert.strictEqual(shownTheme(a.stdout), shownTheme(b.stdout), `iter ${i}`);
    const ra = inProc({ home, env });
    const rb = sub({ home, env });
    assert.deepStrictEqual([...colorsOf(ra.stdout)].sort(), [...colorsOf(rb.stdout)].sort(), `iter ${i} colores`);
  }
});

test('P1 fijo: claves de prototipo, mayusculas, espacios, unicode, control, no-strings (subprocess real)', () => {
  const values = [...PROTO_KEYS, ...WEIRD.map(forSpawn), null, 0, 1, -1, 3.14, true, false, [], ['nord'],
    {}, { nord: true }, { theme: 'nord' }, ...NAMES];
  for (const v of values) {
    const home = tempHome();
    fs.writeFileSync(stateFile(home), JSON.stringify({ theme: v }));
    checkProperty(sub, home, {}, expectedTheme(v, undefined), `theme=${JSON.stringify(v)}`);
  }
});

test('P1 fuzz: 2000 valores aleatorios de theme en el archivo (seed 1337)', () => {
  const r = lcg(1337);
  const home = tempHome();
  const file = stateFile(home);
  for (let i = 0; i < 2000; i++) {
    const v = randValue(r);
    fs.writeFileSync(file, JSON.stringify({ theme: v, mode: 'experto' }));
    checkProperty(inProc, home, {}, expectedTheme(v, undefined), `seed=1337 iter=${i} theme=${JSON.stringify(v)}`);
  }
});

test('P2 fijo: prioridad archivo valido > env valido > templado (subprocess real)', () => {
  const fileVals = [undefined, 'nord', '__proto__', 'NORD', ' gruvbox ', null, 7, ['nord'], 'toString'];
  const envVals = ['', 'catppuccin', '__proto__', 'constructor', 'Templado', ' nord ', 'hasOwnProperty', 'gruvbox', 'valueOf', '\x1b[31m'];
  for (const fv of fileVals) {
    for (const ev of envVals) {
      const home = tempHome();
      if (fv !== undefined) fs.writeFileSync(stateFile(home), JSON.stringify({ theme: fv }));
      checkProperty(sub, home, { STATUSLINE_THEME: ev }, expectedTheme(fv, ev), `file=${JSON.stringify(fv)} env=${JSON.stringify(ev)}`);
    }
  }
});

test('P2 fuzz: 2000 combinaciones archivo x STATUSLINE_THEME (seed 4242)', () => {
  const r = lcg(4242);
  const home = tempHome();
  const file = stateFile(home);
  for (let i = 0; i < 2000; i++) {
    const fv = r.next() < 0.15 ? undefined : randValue(r);
    const ev = r.next() < 0.1 ? undefined : randString(r);
    if (fv === undefined) { try { fs.unlinkSync(file); } catch { /* no estaba */ } } else fs.writeFileSync(file, JSON.stringify({ theme: fv }));
    const env = ev === undefined ? {} : { STATUSLINE_THEME: ev };
    checkProperty(inProc, home, env, expectedTheme(fv, ev), `seed=4242 iter=${i} file=${JSON.stringify(fv)} env=${JSON.stringify(ev)}`);
  }
});

test('P3: statusline.json roto (BOM, CRLF, __proto__ literal, duplicadas, enorme, directorio)', () => {
  const cases = [
    // [nombre, contenido, env, esperado]
    // El BOM UTF-8 (Notepad, PowerShell 5) se saca antes de JSON.parse: el archivo vale.
    ['BOM + tema valido', '\uFEFF{"theme":"nord"}', {}, 'nord'],
    ['BOM + tema valido, env valido', '\uFEFF{"theme":"nord"}', { STATUSLINE_THEME: 'gruvbox' }, 'nord'],
    ['BOM + JSON roto', '\uFEFF{"theme":"nord"', { STATUSLINE_THEME: 'gruvbox' }, 'gruvbox'],
    ['doble BOM (solo se saca uno)', '\uFEFF\uFEFF{"theme":"nord"}', {}, 'templado'],
    ['CRLF', '{\r\n  "theme": "nord"\r\n}\r\n', {}, 'nord'],
    ['__proto__ literal con theme adentro', '{"__proto__":{"theme":"nord"}}', {}, 'templado'],
    ['__proto__ literal + env', '{"__proto__":{"theme":"nord"}}', { STATUSLINE_THEME: 'catppuccin' }, 'catppuccin'],
    ['__proto__ string', '{"__proto__":"nord","theme":"gruvbox"}', {}, 'gruvbox'],
    ['constructor.prototype', '{"constructor":{"prototype":{"theme":"nord"}}}', {}, 'templado'],
    ['duplicadas: valido luego invalido', '{"theme":"nord","theme":"NORD"}', {}, 'templado'],
    ['duplicadas: invalido luego valido', '{"theme":"NORD","theme":"nord"}', {}, 'nord'],
    ['JSON truncado', '{"theme":"nord"', {}, 'templado'],
    ['vacio', '', {}, 'templado'],
    ['solo null', 'null', { STATUSLINE_THEME: 'nord' }, 'nord'],
    ['array top-level', '[{"theme":"nord"}]', {}, 'templado'],
    ['string top-level', '"nord"', {}, 'templado'],
    ['tema con escape unicode', '{"theme":"\\u006eord"}', {}, 'nord'],
    ['tema con NUL escapado', '{"theme":"nord\\u0000"}', {}, 'templado'],
    ['enorme (~8 MB) + tema valido', `{"pad":"${'x'.repeat(8 * 1024 * 1024)}","theme":"gruvbox"}`, {}, 'gruvbox'],
    ['enorme anidado', `${'['.repeat(5000)}${']'.repeat(5000)}`, {}, 'templado'],
  ];
  for (const [name, content, env, expected] of cases) {
    const home = tempHome();
    fs.writeFileSync(stateFile(home), content);
    checkProperty(sub, home, env, expected, name);
    // Sin prototype pollution en el proceso del test tampoco (in-proc comparte realm).
    inProc({ home, args: ['mode'], env });
    assert.strictEqual(({}).theme, undefined, `${name}: Object.prototype contaminado`);
    // mode <x> despues: escribe un objeto JSON valido y el tema sigue valido.
    const w = sub({ home, args: ['mode', 'simple'], env });
    assert.strictEqual(w.status, 0, `${name}: mode simple fallo: ${w.stderr}`);
    assert.doesNotMatch(w.stdout + w.stderr, STACK_RE, `${name}: stack`);
    const st = JSON.parse(fs.readFileSync(stateFile(home), 'utf8'));
    assert.ok(st && typeof st === 'object' && !Array.isArray(st), `${name}: archivo no es objeto`);
    assert.strictEqual(st.mode, 'simple');
    assert.ok(valid(shownTheme(sub({ home, args: ['mode'], env }).stdout)), `${name}: tema invalido despues`);
  }
});

test('P3: statusline.json es un directorio -> render ok, mode <x> falla limpio sin stack', () => {
  const home = tempHome();
  const file = stateFile(home);
  fs.mkdirSync(file);
  checkProperty(sub, home, {}, 'templado', 'dir');
  checkProperty(sub, home, { STATUSLINE_THEME: 'nord' }, 'nord', 'dir+env');
  for (const arg of ['nord', 'simple', 'avisos']) {
    const w = sub({ home, args: ['mode', arg] });
    assert.notStrictEqual(w.status, 0, `mode ${arg} sobre un dir deberia fallar`);
    assert.doesNotMatch(w.stdout, STACK_RE, 'stack en stdout');
    assert.doesNotMatch(w.stderr, STACK_RE, `stack en stderr: ${w.stderr}`);
    assert.ok(fs.statSync(file).isDirectory(), 'el directorio desaparecio');
    const leftovers = fs.readdirSync(path.dirname(file)).filter((f) => f.endsWith('.tmp'));
    assert.deepStrictEqual(leftovers, [], 'quedaron .tmp');
  }
});

// Invariantes despues de cada `mode <x>`: archivo = objeto JSON valido; theme
// solo cambia a un valor valido (o queda el previo, que pudo ser basura sembrada);
// otras claves intactas; mode sin arg muestra un tema valido == render.
function fuzzModeArgs(runner, seed, iters) {
  const r = lcg(seed);
  const home = tempHome();
  const file = stateFile(home);
  const seedVals = [undefined, '__proto__', 'NORD', 42, null, ['nord'], 'gruvbox'];
  let prev = { theme: r.pick(seedVals), keep: 'me', cutFraction: 0.25 };
  fs.writeFileSync(file, JSON.stringify(prev));
  prev = JSON.parse(fs.readFileSync(file, 'utf8'));
  for (let i = 0; i < iters; i++) {
    const ctx = `seed=${seed} iter=${i}`;
    let arg = r.next() < 0.3 ? r.pick([...NAMES, 'simple', 'normal', 'experto', 'silencio', 'avisos']) : randString(r);
    if (runner === sub) arg = forSpawn(arg);
    const env = r.next() < 0.3 ? { STATUSLINE_THEME: runner === sub ? forSpawn(randString(r)) : randString(r) } : {};
    const w = runner({ home, args: ['mode', arg], env });
    assert.ok(!w.crash, `${ctx} arg=${JSON.stringify(arg)}: crash ${w.crash && w.crash.stack}`);
    assert.doesNotMatch(w.stdout, STACK_RE, `${ctx}: stack en stdout`);
    assert.doesNotMatch(w.stderr, STACK_RE, `${ctx}: stack en stderr`);
    const isKnown = valid(arg) || ['simple', 'normal', 'experto', 'silencio', 'avisos'].includes(arg);
    assert.strictEqual(w.status, isKnown || arg === '' ? 0 : 1, `${ctx} arg=${JSON.stringify(arg)}: status ${w.status}`);
    const st = JSON.parse(fs.readFileSync(file, 'utf8'));
    assert.ok(st && typeof st === 'object' && !Array.isArray(st), `${ctx}: archivo no es objeto`);
    assert.strictEqual(st.keep, 'me', `${ctx}: perdio claves`);
    assert.strictEqual(st.cutFraction, 0.25, `${ctx}: perdio cutFraction`);
    if (valid(arg)) assert.strictEqual(st.theme, arg, `${ctx}: no guardo el tema`);
    else assert.deepStrictEqual(st.theme, prev.theme, `${ctx} arg=${JSON.stringify(arg)}: escribio theme=${JSON.stringify(st.theme)}`);
    // El mensaje de confirmacion tambien muestra un tema valido y efectivo.
    const shownAfterWrite = shownTheme(w.stdout);
    assert.ok(valid(shownAfterWrite), `${ctx}: mensaje con tema invalido ${JSON.stringify(w.stdout)}`);
    if (isKnown) assert.strictEqual(shownAfterWrite, expectedTheme(st.theme, env.STATUSLINE_THEME), `${ctx}: confirmacion != efectivo`);
    if (i % 10 === 0 || runner === sub) checkProperty(runner, home, env, expectedTheme(st.theme, env.STATUSLINE_THEME), ctx);
    prev = st;
  }
}

test('P4 fuzz: 2000 `mode <x>` aleatorios in-process (seed 99)', () => {
  fuzzModeArgs(inProc, 99, 2000);
});

test('P4 fuzz: 60 `mode <x>` aleatorios por subprocess real (seed 2024)', () => {
  fuzzModeArgs(sub, 2024, 60);
});

test('P5: ningun valor raro produce stack trace (mode y render, stdout+stderr)', () => {
  const r = lcg(31337);
  const home = tempHome();
  const file = stateFile(home);
  for (let i = 0; i < 2000; i++) {
    const k = r.int(4);
    let content;
    if (k === 0) content = JSON.stringify({ theme: randValue(r), mode: randValue(r), quiet: randValue(r), cutFraction: r.pick([0.25, '0.5', null, -1, 'x', true]) }); // objetos en cutFraction: ver test BUG abajo
    else if (k === 1) content = randString(r) + randString(r);
    else if (k === 2) content = JSON.stringify(randValue(r));
    else content = `{"theme":${JSON.stringify(randString(r))},"__proto__":${JSON.stringify(randValue(r))}}`;
    fs.writeFileSync(file, content);
    const env = { STATUSLINE_THEME: randString(r), STATUSLINE_MODE: randString(r) };
    for (const args of [['mode'], []]) {
      const o = inProc({ home, args, env, input: r.next() < 0.5 ? RICH : randString(r) });
      const ctx = `seed=31337 iter=${i} content=${JSON.stringify(content)} args=${args}`;
      assert.ok(!o.crash, `${ctx}: crash ${o.crash && o.crash.stack}`);
      assert.doesNotMatch(o.stdout, STACK_RE, ctx);
      assert.doesNotMatch(o.stderr, STACK_RE, ctx);
      if (args.length) assert.ok(valid(shownTheme(o.stdout)), `${ctx}: tema invalido ${o.stdout}`);
    }
    assert.strictEqual(({}).theme, undefined, 'Object.prototype contaminado');
  }
});

// Encontrado por el fuzz de P5 (seed=31337 iter=345): cutFraction() hacia
// Number(st.cutFraction) sin proteccion; un objeto cuyo toString/valueOf no es
// funcion tiraba TypeError -> render con stack trace, exit 1 y barra en blanco.
// Repro: statusline.json = {"cutFraction":{"toString":[]}} y `echo {} | node statusline.js`.
// Fix: cutFraction usa num() (solo number o string numerico).
test('cutFraction objeto hostil: el render no crashea y usa la mitad de la ventana', () => {
  const home = tempHome();
  fs.writeFileSync(stateFile(home), '{"cutFraction":{"toString":[]}}');
  const r = sub({ home, input: '{}' });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.doesNotMatch(r.stderr, STACK_RE);
  assert.ok(r.stdout.length > 0, 'barra en blanco');
});

test('cutFraction: solo number o string numerico en (0,1); lo demas = 0.5', () => {
  // Uso 120k de 200k: con 0.5 (corte 100k) es "charla larga"; con 0.75 (150k) no.
  const input = JSON.stringify({ context_window: { context_window_size: 200000, current_usage: { input_tokens: 120000 } } });
  const cases = [
    [0.75, false], ['0.75', false], [' 0.75 ', false], [0.5, true], [{ toString: [] }, true], [{ valueOf: [] }, true],
    [[0.75], true], [['0.75'], true], [{}, true], ['', true], [' ', true], [true, true], [null, true], [0, true], [1, true],
    [-0.25, true], ['Infinity', true], ['1e400', true], ['abc', true],
  ];
  for (const [v, long] of cases) {
    const home = tempHome();
    fs.writeFileSync(stateFile(home), JSON.stringify({ mode: 'experto', quiet: false, cutFraction: v }));
    const o = inProc({ home, input });
    assert.ok(!o.crash, `${JSON.stringify(v)}: crash ${o.crash && o.crash.stack}`);
    assert.strictEqual(o.status, 0, `${JSON.stringify(v)}: exit ${o.status}`);
    assert.strictEqual(o.stdout.includes('charla larga'), long, `cutFraction=${JSON.stringify(v)}: ${o.stdout}`);
  }
});

// --- Fuzz de coerciones: objetos con toString/valueOf hostiles en CADA clave ---
// Un valor de JSON nunca trae funciones, pero si un objeto con una propiedad
// propia "toString"/"valueOf" que no es callable: Number(x), `${x}`, x + '' o
// String(x) sobre el tiran TypeError. La barra no puede caerse por eso.
const HOSTILE = [
  { toString: [] }, { valueOf: [] }, { toString: [], valueOf: [] }, { toString: {}, valueOf: {} },
  { toString: 1, valueOf: 'x' }, { toJSON: [], toString: null }, { constructor: { toString: [] }, toString: [] },
  [{ toString: [] }], [[]], [], {}, { length: { toString: [] } }, { 0: { valueOf: [] } }, '{"toString":[]}',
  'Infinity', '1e400', '-1', 1e308, -1e308, -1, null, true,
];
const FILE_KEYS = ['mode', 'theme', 'quiet', 'cutFraction', 'extra', 'toString', 'valueOf'];
// Todos los caminos del stdin que lee collect(); tambien cada objeto intermedio entero.
const STDIN_PATHS = [
  'model', 'model.display_name', 'model.id',
  'context_window', 'context_window.context_window_size', 'context_window.used_percentage', 'context_window.current_usage',
  'context_window.current_usage.input_tokens', 'context_window.current_usage.cache_read_input_tokens',
  'context_window.current_usage.cache_creation_input_tokens',
  'transcript_path', 'cwd', 'workspace', 'workspace.current_dir',
  'rate_limits', 'rate_limits.five_hour', 'rate_limits.five_hour.used_percentage', 'rate_limits.five_hour.resets_at',
  'rate_limits.seven_day', 'rate_limits.seven_day.used_percentage', 'rate_limits.seven_day.resets_at',
  'prompt_cache', 'prompt_cache.hit_ratio', 'prompt_cache.expires_at', 'prompt_cache.warm', 'prompt_cache.last_miss_cause',
  'prompt_cache.miss_causes', 'prompt_cache.miss_causes.tools_changed', 'prompt_cache.recache_tokens_if_cold', 'prompt_cache.ttl',
  'cost', 'cost.total_cost_usd', 'effort', 'effort.level', 'fast_mode', 'thinking', 'thinking.enabled',
];
const RICH_OBJ = JSON.parse(RICH);
// Base con cache fria + miss_causes para que los render recorran todas las ramas.
const BASE = {
  ...RICH_OBJ, transcript_path: '', cwd: '', effort: { level: 'high' }, fast_mode: true, thinking: { enabled: true },
  prompt_cache: { ...RICH_OBJ.prompt_cache, warm: false, hit_ratio: 0.4, miss_causes: { tools_changed: 3, model_changed: 1 },
    recache_tokens_if_cold: 120000, ttl: '1h' },
};
function withPath(obj, dotted, value) {
  const out = structuredClone(obj);
  const keys = dotted.split('.');
  let cur = out;
  for (const k of keys.slice(0, -1)) {
    if (!cur[k] || typeof cur[k] !== 'object') cur[k] = {};
    cur = cur[k];
  }
  cur[keys[keys.length - 1]] = value;
  return out;
}
const ser = (v) => JSON.stringify(v);
// allowBlank: modo simple en silencio sin plan ni contexto conocidos no tiene
// nada que mostrar (linea vacia por diseno, no una caida).
function renderOk(home, input, ctx, allowBlank = false) {
  const o = inProc({ home, input });
  assert.ok(!o.crash, `${ctx}: crash ${o.crash && o.crash.stack}`);
  assert.strictEqual(o.status, 0, `${ctx}: exit ${o.status}`);
  assert.doesNotMatch(o.stdout + o.stderr, STACK_RE, ctx);
  // Un texto del stdin (modelo, esfuerzo) puede ser literalmente "Infinity" y se
  // muestra tal cual; lo que no puede salir es un NUMERO no finito formateado.
  assert.doesNotMatch(o.stdout, /NaN|undefined|\[object|Infinity(%|k|M|m\b)|\$Infinity|-?\d+(\.\d+)?e[+-]\d/, `${ctx}: basura: ${o.stdout}`);
  if (!allowBlank) assert.ok(o.stdout.trim().length > 0, `${ctx}: barra en blanco`);
}

test('fuzz hostil: cada clave de statusline.json con cada valor hostil, en los 3 modos (nunca se cae)', () => {
  const home = tempHome();
  const file = stateFile(home);
  let n = 0;
  for (const mode of ['simple', 'normal', 'experto']) {
    for (const key of FILE_KEYS) {
      for (const v of HOSTILE) {
        const st = { mode, quiet: false, theme: 'nord', cutFraction: 0.25, [key]: v };
        fs.writeFileSync(file, ser(st));
        renderOk(home, ser(BASE), `mode=${mode} statusline.json ${key}=${ser(v)}`);
        // `mode` sin arg tambien lee el archivo.
        const m = inProc({ home, args: ['mode'] });
        assert.ok(!m.crash && m.status === 0, `mode ${key}=${ser(v)}: ${m.crash && m.crash.stack}`);
        n++;
      }
    }
  }
  assert.strictEqual(n, 3 * FILE_KEYS.length * HOSTILE.length);
});

test('fuzz hostil: cada camino del stdin con cada valor hostil, en los 3 modos (nunca se cae)', () => {
  const home = tempHome();
  const file = stateFile(home);
  for (const mode of ['simple', 'normal', 'experto']) {
    fs.writeFileSync(file, JSON.stringify({ mode, quiet: false }));
    for (const p of STDIN_PATHS) {
      for (const v of HOSTILE) renderOk(home, ser(withPath(BASE, p, v)), `mode=${mode} stdin ${p}=${ser(v)}`);
    }
    for (const v of HOSTILE) renderOk(home, ser(v), `mode=${mode} stdin entero=${ser(v)}`);
  }
});

test('fuzz hostil combinado (LCG seed=777): varias claves hostiles a la vez en archivo y stdin', () => {
  const r = lcg(777);
  const home = tempHome();
  const file = stateFile(home);
  for (let i = 0; i < 1500; i++) {
    const st = { mode: r.pick(['simple', 'normal', 'experto']), quiet: r.next() < 0.5 ? false : r.pick(HOSTILE) };
    for (const k of FILE_KEYS) if (r.next() < 0.4) st[k] = r.pick(HOSTILE);
    fs.writeFileSync(file, ser(st));
    let input = BASE;
    for (const p of STDIN_PATHS) if (r.next() < 0.15) input = withPath(input, p, r.pick(HOSTILE));
    renderOk(home, ser(input), `seed=777 iter=${i} file=${ser(st)} stdin=${ser(input)}`, st.mode === 'simple' && st.quiet !== false);
  }
});

test('fuzz hostil en subprocess real (muestra): exit 0, sin stack y barra no vacia', () => {
  const home = tempHome();
  const file = stateFile(home);
  for (const v of [{ toString: [] }, { valueOf: [] }, [{ toString: [] }]]) {
    for (const key of ['cutFraction', 'theme', 'mode', 'quiet']) {
      fs.writeFileSync(file, ser({ [key]: v }));
      const input = ser(withPath(withPath(BASE, 'context_window.context_window_size', v), 'prompt_cache.hit_ratio', v));
      const o = sub({ home, input });
      assert.strictEqual(o.status, 0, `${key}=${ser(v)}: ${o.stderr}`);
      assert.doesNotMatch(o.stderr, STACK_RE);
      assert.ok(o.stdout.trim().length > 0, `${key}=${ser(v)}: barra en blanco`);
    }
  }
});

test('BOM: statusline.json, flags y stdin con BOM se leen igual que sin BOM', () => {
  const home = tempHome();
  const file = stateFile(home);
  const dir = path.dirname(file);
  fs.writeFileSync(file, '﻿{"mode":"experto","theme":"gruvbox","quiet":false,"cutFraction":0.75}');
  fs.writeFileSync(path.join(dir, 'caveman.json'), '﻿{"on":true,"level":"full"}');
  fs.writeFileSync(path.join(dir, 'verify.json'), '﻿{"on":true}');
  const input = '﻿' + JSON.stringify({ model: { display_name: 'Opus BOM' }, context_window: { context_window_size: 200000, current_usage: { input_tokens: 120000 } } });
  const o = sub({ home, input });
  assert.strictEqual(o.status, 0, o.stderr);
  assert.match(o.stdout, /Opus BOM/, 'stdin con BOM se ignoro');
  assert.match(o.stdout, /caveman:full/, 'caveman.json con BOM se ignoro');
  assert.match(o.stdout, /verify/, 'verify.json con BOM se ignoro');
  assert.doesNotMatch(o.stdout, /charla larga/, 'cutFraction 0.75 del archivo con BOM no se aplico');
  assert.deepStrictEqual(themesMatching(colorsOf(o.stdout)), ['gruvbox']);
  // `mode` reescribe el archivo sin BOM y conserva las claves.
  assert.strictEqual(sub({ home, args: ['mode', 'simple'] }).status, 0);
  const back = fs.readFileSync(file, 'utf8');
  assert.notStrictEqual(back.charCodeAt(0), 0xfeff);
  assert.deepStrictEqual(JSON.parse(back), { mode: 'simple', theme: 'gruvbox', quiet: false, cutFraction: 0.75 });
});

test('STATUSLINE_CUT_TOKENS: solo un numero finito > 0 cuenta', () => {
  const input = JSON.stringify({ context_window: { context_window_size: 200000, current_usage: { input_tokens: 120000 } } });
  for (const [env, long] of [['150000', false], ['100000', true], ['Infinity', true], ['1e400', true], ['-5', true], ['0', true], ['abc', true], ['', true]]) {
    const home = tempHome();
    fs.writeFileSync(stateFile(home), JSON.stringify({ quiet: false }));
    const o = inProc({ home, input, env: { STATUSLINE_CUT_TOKENS: env } });
    assert.strictEqual(o.status, 0);
    assert.strictEqual(o.stdout.includes('charla larga'), long, `STATUSLINE_CUT_TOKENS=${JSON.stringify(env)}: ${o.stdout}`);
  }
});
