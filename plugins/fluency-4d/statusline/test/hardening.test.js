// Entradas hostiles (ataque adversarial): claves del prototipo, caracteres de
// control, EPERM en el rename, git roto, estado no-objeto, numeros invalidos y
// stdin que no cierra.
const test = require('node:test');
const assert = require('node:assert');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { SCRIPT, tempHome, flagsDir, run } = require('./helpers');

const PRELOAD = path.join(__dirname, 'rename_fail.js');
const nowSec = () => Math.floor(Date.now() / 1000);

function runMode(home, arg, env = {}) {
  return spawnSync(process.execPath, ['-r', PRELOAD, SCRIPT, 'mode', arg], {
    encoding: 'utf8',
    env: { ...process.env, HOME: home, USERPROFILE: home, ...env },
    timeout: 20000,
  });
}

const tmpLeft = (home) => fs.readdirSync(flagsDir(home)).filter((f) => f.endsWith('.tmp'));

// --- 3. Claves del prototipo ---
for (const key of ['toString', '__proto__', 'valueOf', 'constructor']) {
  test(`mode ${key} se rechaza: Uso, exit 1 y no escribe`, () => {
    const home = tempHome();
    const r = run({ home, args: ['mode', key] });
    assert.strictEqual(r.status, 1, r.stderr);
    assert.match(r.stdout, /Uso:/);
    assert.ok(!fs.existsSync(path.join(home, '.claude', 'fluency4d', 'statusline.json')));
  });
}

test('STATUSLINE_THEME=valueOf se ignora (tokyo-night)', () => {
  // run() borra STATUSLINE_THEME del env: aca se lanza a mano.
  const home = tempHome();
  const r = spawnSync(process.execPath, [SCRIPT], {
    input: JSON.stringify({ model: { display_name: 'X' } }),
    encoding: 'utf8',
    env: { ...process.env, HOME: home, USERPROFILE: home, STATUSLINE_MODE: 'normal', STATUSLINE_THEME: 'valueOf' },
    timeout: 20000,
  });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.doesNotMatch(r.stdout, /undefined/);
  // tokyo-night: modelo en 7aa2f7 = 122;162;247
  assert.ok(r.stdout.includes('\x1b[38;2;122;162;247m'), r.stdout);
});

test('theme "toString" en statusline.json se ignora', () => {
  const home = tempHome();
  fs.writeFileSync(path.join(flagsDir(home), 'statusline.json'), '{"theme":"toString","mode":"normal"}');
  const r = run({ home, mode: null, input: {} });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('\x1b[38;2;122;162;247m'));
});

// --- 4. Caracteres de control ---
test('display_name, effort, miss cause y rama sin caracteres de control', () => {
  const root = tempHome();
  fs.mkdirSync(path.join(root, '.git'));
  fs.writeFileSync(path.join(root, '.git', 'HEAD'), 'ref: refs/heads/ma\x1b[31min\x07\n');
  const r = run({
    input: {
      model: { display_name: 'Op\x1b[2Jus\r\x9b' },
      effort: { level: 'hi\x1bgh' },
      workspace: { current_dir: root },
      prompt_cache: { warm: true, hit_ratio: 0.5, last_miss_cause: 'model\x1b]0;pwn\x07_change' },
    },
  });
  assert.strictEqual(r.status, 0, r.stderr);
  // Unicos ESC: los SGR propios de la barra.
  const foreign = r.stdout.replace(/\x1b\[[0-9;]*m/g, '');
  assert.doesNotMatch(foreign, /[\x00-\x09\x0b-\x1f\x7f-\x9f]/);
  assert.match(r.plain, /Op\[2Jus/);
  assert.match(r.plain, /hi\[?gh/);
  assert.match(r.plain, /⎇ ma\[31min/);
  assert.match(r.plain, /model\]0;pwn change/);
});

test('miss_causes con claves de control se limpian', () => {
  const r = run({ input: { prompt_cache: { warm: true, hit_ratio: 0.5, miss_causes: { 'a\x1bb': 3, c: 1 } } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.doesNotMatch(r.stdout.replace(/\x1b\[[0-9;]*m/g, ''), /\x1b/);
  assert.match(r.plain, /\(ab\)/);
});

// --- 5. EPERM en el rename ---
test('rename con EPERM transitorio: reintenta y guarda', () => {
  const home = tempHome();
  const r = runMode(home, 'simple', { FAIL_RENAMES: '3' });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.strictEqual(JSON.parse(fs.readFileSync(path.join(flagsDir(home), 'statusline.json'), 'utf8')).mode, 'simple');
  assert.deepStrictEqual(tmpLeft(home), []);
});

for (const code of ['EBUSY', 'EACCES']) {
  test(`rename con ${code} transitorio: reintenta`, () => {
    const home = tempHome();
    const r = runMode(home, 'experto', { FAIL_RENAMES: '2', FAIL_RENAME_CODE: code });
    assert.strictEqual(r.status, 0, r.stderr);
  });
}

test('rename que sigue fallando: mensaje limpio, exit != 0, sin stack ni .tmp', () => {
  const home = tempHome();
  const r = runMode(home, 'simple', { FAIL_RENAMES: '99' });
  assert.notStrictEqual(r.status, 0);
  assert.match(r.stderr, /No pude guardar .*EPERM/);
  assert.doesNotMatch(r.stderr, /\n\s+at /);
  assert.deepStrictEqual(tmpLeft(home), []);
});

// --- 6. gitBranch ---
test('HEAD es una carpeta (EISDIR): sin rama y sin romper', () => {
  const root = tempHome();
  fs.mkdirSync(path.join(root, '.git', 'HEAD'), { recursive: true });
  const r = run({ input: { workspace: { current_dir: root } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.doesNotMatch(r.plain, /⎇/);
});

test('current_dir/cwd no-string: sin rama y sin romper', () => {
  for (const input of [{ workspace: { current_dir: 42 } }, { cwd: { a: 1 } }, { workspace: { current_dir: ['x'] }, cwd: 7 }]) {
    const r = run({ input });
    assert.strictEqual(r.status, 0, r.stderr);
    assert.doesNotMatch(r.plain, /⎇/);
  }
});

test('.git con gitdir inexistente: null, no sube al repo padre', () => {
  const parent = tempHome();
  fs.mkdirSync(path.join(parent, '.git'));
  fs.writeFileSync(path.join(parent, '.git', 'HEAD'), 'ref: refs/heads/padre\n');
  const child = path.join(parent, 'sub');
  fs.mkdirSync(child);
  fs.writeFileSync(path.join(child, '.git'), `gitdir: ${path.join(parent, 'no-existe')}\n`);
  const r = run({ input: { workspace: { current_dir: child } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.doesNotMatch(r.plain, /⎇/);
});

// --- 7. readState ---
for (const raw of ['42', '[1,2]', 'null', '"texto"']) {
  test(`statusline.json = ${raw}: mode escribe un objeto valido`, () => {
    const home = tempHome();
    const file = path.join(flagsDir(home), 'statusline.json');
    fs.writeFileSync(file, raw);
    const r = run({ home, args: ['mode', 'simple'] });
    assert.strictEqual(r.status, 0, r.stderr);
    assert.deepStrictEqual(JSON.parse(fs.readFileSync(file, 'utf8')), { mode: 'simple' });
  });
}

// --- 8. Numeros ---
test('resets_at invalido: omite "vuelve" y no pinta NaN', () => {
  for (const resets_at of ['nope', 1e300, -5, null, { x: 1 }]) {
    const r = run({ input: { rate_limits: { five_hour: { used_percentage: 40, resets_at } } } });
    assert.strictEqual(r.status, 0, r.stderr);
    assert.match(r.plain, /5h .*40%/);
    assert.doesNotMatch(r.plain, /vuelve|NaN/);
  }
});

test('used_percentage no finito: no se muestra el plan', () => {
  const r = run({ input: { rate_limits: { five_hour: { used_percentage: Number.NaN } } } });
  assert.doesNotMatch(r.plain, /5h|NaN/);
});

test('expires_at en ms se convierte a segundos', () => {
  const r = run({ input: { prompt_cache: { warm: true, hit_ratio: 0.96, expires_at: (nowSec() + 25 * 60 + 30) * 1000 } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.match(r.plain, /vence en 25m/);
});

test('expires_at no numerico: sin "vence en"', () => {
  const r = run({ input: { prompt_cache: { warm: true, hit_ratio: 0.96, expires_at: 'mañana' } } });
  assert.doesNotMatch(r.plain, /vence en|NaN/);
});

test('context_window_size <= 0 o invalido: usa el default', () => {
  for (const context_window_size of [0, -100, 'x', null]) {
    const r = run({ input: { context_window: { context_window_size, current_usage: { input_tokens: 100_000 } } } });
    assert.strictEqual(r.status, 0, r.stderr);
    assert.match(r.plain, /ctx .*50% 100\.0k\/200\.0k/);
    assert.doesNotMatch(r.plain, /Infinity|NaN/);
  }
});

test('tokens como string se convierten; no finitos = null', () => {
  let r = run({ input: { context_window: { context_window_size: 200_000, current_usage: { input_tokens: '50000', cache_read_input_tokens: '50000' } } } });
  assert.match(r.plain, /ctx .*50% 100\.0k\/200\.0k/);
  r = run({ input: { context_window: { context_window_size: 200_000, current_usage: { input_tokens: 'mucho' } } } });
  assert.doesNotMatch(r.plain, /NaN/);
  assert.match(r.plain, /ctx —/);
});

test('costo no numerico: no se muestra', () => {
  const r = run({ input: { cost: { total_cost_usd: 'gratis' } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.doesNotMatch(r.plain, /sesión/);
});

test('stdin que no cierra: renderiza a los 2 s con lo que haya y sale', async () => {
  const home = tempHome();
  const child = spawn(process.execPath, [SCRIPT], {
    env: { ...process.env, HOME: home, USERPROFILE: home, STATUSLINE_MODE: 'experto' },
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  let out = '';
  child.stdout.on('data', (c) => (out += c));
  child.stdin.write('{"model":{"display_name":"Lento"}}'); // nunca end()
  const started = Date.now();
  const code = await new Promise((resolve) => {
    const kill = setTimeout(() => { child.kill(); resolve('timeout'); }, 8000);
    child.on('exit', (c) => { clearTimeout(kill); resolve(c); });
  });
  assert.strictEqual(code, 0);
  assert.ok(Date.now() - started < 6000);
  assert.match(out, /Lento/);
});
