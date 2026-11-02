// Paridad de fmtTokens entre el panel (hooks/register.tsx) y la barra
// (statusline/statusline.js). Extrae las DOS funciones reales del fuente (sin
// copias), las evalua y las compara con fuzzing de semilla fija.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { REPO_ROOT, run, tempHome } = require('./helpers');

const PLUGIN = path.join(REPO_ROOT, 'plugins', 'fluency-4d');
const SRC = {
  panel: path.join(PLUGIN, 'hooks', 'register.tsx'),
  barra: path.join(PLUGIN, 'statusline', 'statusline.js'),
};

// Extrae `function fmtTokens(<params>)[: string] { ... }` (cuerpo hasta la `}`
// en columna 0). Falla claro si no hay exactamente una, si cambia la firma o si
// el cuerpo trae sintaxis TS que no se puede evaluar como JS.
function extract(label, file) {
  const src = fs.readFileSync(file, 'utf8');
  const re = /^function fmtTokens\s*\(([^)]*)\)\s*(?::\s*([\w<>[\]| ]+?))?\s*\{\n([\s\S]*?)\n\}/gm;
  const all = [...src.matchAll(re)];
  assert.strictEqual(all.length, 1, `${label}: se esperaba UNA definicion top-level de fmtTokens en ${file}, hay ${all.length}`);
  const [, rawParams, ret, body] = all[0];
  const params = rawParams.split(',').map((p) => p.trim()).filter(Boolean);
  assert.strictEqual(params.length, 1, `${label}: firma cambiada, fmtTokens(${rawParams}) — se esperaba 1 parametro`);
  const [name, type] = params[0].split(':').map((s) => s.trim());
  assert.strictEqual(name, 'n', `${label}: firma cambiada, parametro "${name}" (se esperaba "n")`);
  if (label === 'panel') {
    assert.strictEqual(type, 'number', `${label}: tipo del parametro cambio a "${type}"`);
    assert.strictEqual(ret, 'string', `${label}: tipo de retorno cambio a "${ret}"`);
  }
  let fn;
  try {
    fn = new Function(name, body); // eslint-disable-line no-new-func
  } catch (e) {
    assert.fail(`${label}: el cuerpo de fmtTokens no es JS evaluable (¿sintaxis TS nueva?): ${e.message}\n${body}`);
  }
  return fn;
}

const panel = extract('panel', SRC.panel);
const barra = extract('barra', SRC.barra);

// PRNG determinista (mulberry32), semilla fija.
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const EDGES = [
  0, 1, 9, 10, 99, 100, 999, 1000, 1001, 1049, 1050, 1051, 1949, 1950, 9999, 10_000, 99_949, 99_950, 99_951,
  250_000, 999_499, 999_500, 999_949, 999_950, 999_999, 1_000_000, 1_000_001, 1_004_999, 1_005_000, 1_005_001,
  1_500_000, 9_994_999, 9_995_000, 9_999_999, 10_000_000, 99_999_999, 100_000_000, 999_999_999, 1_000_000_000,
  1_999_999_999, 2_000_000_000,
];

const R = rng(0x4d4d4d);
const INTS = [...EDGES];
// Enteros uniformes en 0..2e9 y log-uniformes (para cubrir todos los ordenes).
for (let i = 0; i < 4000; i++) INTS.push(Math.floor(R() * 2e9));
for (let i = 0; i < 4000; i++) INTS.push(Math.min(2e9, Math.floor(10 ** (R() * Math.log10(2e9)))));
// Alrededor de cada borde de unidad/redondeo.
for (const e of EDGES) for (let d = -3; d <= 3; d++) if (e + d >= 0) INTS.push(e + d);

const FLOATS = [];
// Floats con .5 justo en la posicion de redondeo de toFixed (k: 1 dec, M: 2 dec).
for (let i = 0; i < 1500; i++) {
  const k = Math.floor(R() * 999_000) + 1000;
  FLOATS.push(Math.floor(k / 100) * 100 + 50); // x.x5k
  FLOATS.push(Math.floor(R() * 2e9 / 10_000) * 10_000 + 5000); // x.xx5M
  FLOATS.push(R() * 2e6); // float arbitrario
  FLOATS.push(Math.floor(R() * 2000) + 0.5); // n.5 crudo
}

const WEIRD = [
  -0, -1, -999, -1000, -1500, -1_000_000, -2e9, NaN, Infinity, -Infinity, Number.MAX_SAFE_INTEGER, 1e21, 1e22,
  Number.MAX_VALUE, Number.MIN_VALUE, Number.EPSILON, '1500', '1000000', ' 2500 ', '', 'abc', '1e6', null, undefined,
  true, false,
];

const ALL = [...INTS, ...FLOATS, ...WEIRD];

// Ancho maximo en la barra/panel: el peor caso realista en 0..2e9 es
// "2000.00M" (8). Para el uso real (ventanas <=1M, autocompact <=1M) es 6 ("999.9k"); el tope de 7 deja margen. Fuera de dominio (>= 1e10, negativos, no-number) = "—".
const N = 8;

// Numero que "muestra" el string (para monotonia, sin importar la unidad).
function shown(s) {
  const m = /^(-?\d+(?:\.\d+)?)([kM]?)$/.exec(s);
  assert.ok(m, `string no numerico: ${JSON.stringify(s)}`);
  return Number(m[1]) * (m[2] === 'M' ? 1e6 : m[2] === 'k' ? 1e3 : 1);
}

test(`fuzz: ${ALL.length} valores (semilla fija) — panel === barra, exacto`, () => {
  assert.ok(ALL.length > 5000);
  for (const v of ALL) {
    const a = panel(v);
    const b = barra(v);
    assert.strictEqual(typeof a, 'string', `panel(${String(v)}) no es string`);
    assert.strictEqual(a, b, `difieren en ${typeof v} ${JSON.stringify(v) ?? String(v)}: panel=${a} barra=${b}`);
  }
});

test('valores esperados en los bordes (1M, 1.50M, 250.0k, ...)', () => {
  const exp = {
    0: '0', 999: '999', 1000: '1.0k', 9999: '10.0k', 99_950: '100.0k', 250_000: '250.0k', 999_499: '999.5k',
    999_500: '999.5k', 1_000_000: '1M', 1_000_001: '1.00M', 1_500_000: '1.50M', 9_999_999: '10.00M', 10_000_000: '10M',
    2_000_000_000: '2000M',
  };
  for (const [k, v] of Object.entries(exp)) {
    assert.strictEqual(panel(Number(k)), v, `panel(${k})`);
    assert.strictEqual(barra(Number(k)), v, `barra(${k})`);
  }
});

test(`enteros 0..2e9: sin NaN/Infinity/undefined, ancho <= ${N}, formato valido`, () => {
  for (const v of INTS) {
    const s = barra(v);
    assert.ok(!/NaN|Infinity|undefined|e[+-]/.test(s), `basura en ${v}: ${s}`);
    assert.ok(s.length <= N, `ancho ${s.length} > ${N} en ${v}: ${s}`);
    shown(s);
  }
});

test('uso real (0..1M): ancho <= 7', () => {
  for (const v of INTS.filter((x) => x <= 1_000_000)) assert.ok(barra(v).length <= 7, `${v}: ${barra(v)}`);
});

test('floats >= 0 en 0..2e9: sin NaN/Infinity/e+, y el numero mostrado esta a < 0.5% (o 0.05k/0.005M, o 0.5 bajo 1000: se redondea a entero) del real', () => {
  for (const v of FLOATS) {
    const s = barra(v);
    assert.ok(!/NaN|Infinity|undefined|e[+-]/.test(s), `basura en ${v}: ${s}`);
    const err = Math.abs(shown(s) - v);
    const tol = v >= 1e6 ? 5000 + 1e-6 : v >= 999.5 ? 50 + 1e-9 : 0.5;
    assert.ok(err <= tol, `${v} -> ${s} (error ${err})`);
  }
});

test('monotonia: a < b => numero mostrado(a) <= numero mostrado(b), incluso al pasar k -> M', () => {
  const xs = [...new Set([...INTS, ...FLOATS])].sort((a, b) => a - b);
  let prev = -Infinity;
  let prevV = null;
  for (const v of xs) {
    const cur = shown(barra(v));
    assert.ok(cur >= prev - 1e-6, `decrece: ${prevV} -> ${barra(prevV)} pero ${v} -> ${barra(v)}`);
    prev = cur;
    prevV = v;
  }
});

test('fuera de dominio: no-number, NaN, Infinity y negativos dan "—" en las dos', () => {
  // Entradas no alcanzables hoy (la barra filtra con num() y el panel con
  // finiteNum() > 0), pero si un caller nuevo las manda no sale basura:
  // ni "null"/"undefined", ni "InfinityM", ni "-1500" sin unidad.
  for (const v of [null, undefined, '1500', 'abc', '', true, {}, [], NaN, Infinity, -Infinity, -1, -1500, -2e9, -Number.MIN_VALUE]) {
    assert.strictEqual(barra(v), '—', `barra(${String(v)})`);
    assert.strictEqual(panel(v), '—', `panel(${String(v)})`);
  }
  // -0 es >= 0: cuenta como 0.
  assert.strictEqual(barra(-0), '0');
});

test('999_950..999_999 suben a "1.00M" (nunca "1000.0k"); solo M exactos van sin decimales', () => {
  for (let v = 999_950; v <= 999_999; v++) {
    assert.strictEqual(barra(v), '1.00M', `barra(${v})`);
    assert.strictEqual(panel(v), '1.00M', `panel(${v})`);
  }
  for (const v of [999_949, 999_949.99]) assert.strictEqual(barra(v), '999.9k', `barra(${v})`);
  // Decision: 1_004_999 no es un M exacto -> "1.00M" (como 1_000_001), no "1M".
  for (const [v, want] of [[1_000_000, '1M'], [1_000_001, '1.00M'], [1_004_999, '1.00M'], [1_005_000, '1.00M'], [2_000_000, '2M']]) {
    assert.strictEqual(barra(v), want, `barra(${v})`);
    assert.strictEqual(panel(v), want, `panel(${v})`);
  }
  for (const v of ALL) assert.ok(!/^1000.0k$/.test(barra(v)), `${String(v)} -> 1000.0k`);
});

test('panel: Infinity (de "Infinity" o "1e400") no muestra "InfinityM"', () => {
  for (const v of [Infinity, Number('Infinity'), Number('1e400')]) {
    assert.strictEqual(panel(v), '—');
    assert.strictEqual(barra(v), '—');
  }
});

test(`enteros enormes (MAX_SAFE_INTEGER, 1e21, 1e27, MAX_VALUE): ancho <= ${N}, sin notacion cientifica`, () => {
  for (const v of [9_999_994_999, 1e10, Number.MAX_SAFE_INTEGER, 1e21, 1e22, 1e27, Number.MAX_VALUE]) {
    const s = barra(v);
    assert.ok(s.length <= N, `${v}: ${s}`);
    assert.ok(!/e[+-]|Infinity|NaN/.test(s), `${v}: ${s}`);
    assert.strictEqual(panel(v), s);
  }
  // Hasta 9_999_994_999 se formatea; desde ahi el texto pasaria de 8 -> "—".
  assert.strictEqual(barra(9_999_994_999), '9999.99M');
  assert.strictEqual(barra(Number.MAX_SAFE_INTEGER), '—');
});

test(`fuzz: ningun valor (incluso WEIRD) da mas de ${N} caracteres en ninguna de las dos`, () => {
  for (const v of ALL) {
    assert.ok(barra(v).length <= N, `barra(${String(v)}) = ${barra(v)}`);
    assert.ok(panel(v).length <= N, `panel(${String(v)}) = ${panel(v)}`);
  }
});

test('integracion: la barra renderizada muestra el mismo string que el panel', () => {
  for (const [used, size] of [[1_500_000, 2_000_000], [250_000, 1_000_000], [999_999, 1_000_000], [150_000, 200_000]]) {
    const input = JSON.stringify({ context_window: { context_window_size: size, current_usage: { input_tokens: used } } });
    const r = run({ home: tempHome(), input, mode: 'experto' });
    assert.strictEqual(r.status, 0, r.stderr);
    const want = `${panel(used)}/${panel(size)}`;
    assert.ok(r.plain.includes(want), `barra no muestra "${want}":\n${r.plain}`);
  }
});
