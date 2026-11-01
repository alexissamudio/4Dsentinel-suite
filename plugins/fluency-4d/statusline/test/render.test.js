// Render de la status line: casos de cache y entradas degeneradas.
const test = require('node:test');
const assert = require('node:assert');
const { run } = require('./helpers');

const nowSec = () => Math.floor(Date.now() / 1000);
const MODES = ['simple', 'normal', 'experto'];

test('cache caliente: reciclado 96% y vence en 25m', () => {
  const r = run({ input: { prompt_cache: { warm: true, hit_ratio: 0.96, expires_at: nowSec() + 25 * 60 + 30 } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.match(r.plain, /reciclado 96%/);
  assert.match(r.plain, /vence en 25m/);
  assert.doesNotMatch(r.plain, /fría/);
});

test('cache fria con ttl 1h: recarga a 2x y muestra el reciclado anterior', () => {
  const r = run({ input: { prompt_cache: { warm: false, hit_ratio: 0.96, recache_tokens_if_cold: 83100, ttl: '1h' } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(
    r.plain.includes('el próximo msg recarga 83.1k (2x) · antes reciclaba 96%'),
    r.plain,
  );
  assert.doesNotMatch(r.plain, /vence en/);
});

test('cache fria con ttl 5m: recarga a 1.25x', () => {
  const r = run({ input: { prompt_cache: { warm: false, hit_ratio: 0.96, recache_tokens_if_cold: 83100, ttl: 300 } } });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.plain.includes('el próximo msg recarga 83.1k (1.25x)'), r.plain);
});

test('cache vencida por expires_at cuenta como fria', () => {
  const r = run({ input: { prompt_cache: { hit_ratio: 0.9, expires_at: nowSec() - 60, recache_tokens_if_cold: 5000, ttl: 'ephemeral_1h' } } });
  assert.ok(r.plain.includes('recarga 5.0k (2x)'), r.plain);
});

for (const [name, input] of [
  ['sin datos (stdin vacio)', ''],
  ['objeto vacio {}', '{}'],
  ['stdin no-JSON', 'esto no es json'],
  ['null', 'null'],
]) {
  for (const mode of MODES) {
    test(`${name} en modo ${mode}: no rompe y renderiza algo`, () => {
      // Con avisos: en silencio el modo simple sin datos no tiene nada que mostrar.
      const r = run({ input, mode, avisos: true });
      assert.strictEqual(r.status, 0, r.stderr);
      assert.strictEqual(r.stderr, '');
      assert.ok(r.plain.trim().length > 0);
      assert.doesNotMatch(r.plain, /undefined|NaN/);
    });
  }
}

test('sin datos en experto: ctx sin numero', () => {
  const r = run({ input: '{}' });
  assert.match(r.plain, /ctx —/);
});

test('contexto al 95%: porcentaje, tokens y aviso de charla larga', () => {
  const input = { context_window: { context_window_size: 200000, current_usage: { input_tokens: 150000, cache_read_input_tokens: 40000 } } };
  const r = run({ input, avisos: true });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.match(r.plain, /ctx \S+ 95% 190\.0k\/200\.0k charla larga/);
  const simple = run({ input, mode: 'simple', avisos: true });
  assert.match(simple.plain, /Charla larga/);
});

test('defaults sin statusline.json: modo experto, colores de templado y ningun consejo', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const { tempHome } = require('./helpers');
  const home = tempHome();
  const file = path.join(home, '.claude', 'fluency4d', 'statusline.json');
  // Contexto al 95% y cache fria: con avisos habria "charla larga" y un consejo.
  const input = {
    model: { display_name: 'Opus' },
    context_window: { context_window_size: 200000, current_usage: { input_tokens: 150000, cache_read_input_tokens: 40000 } },
    prompt_cache: { warm: false, hit_ratio: 0.5, recache_tokens_if_cold: 83100, ttl: 300 },
  };
  const r = run({ home, input, mode: null });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(!fs.existsSync(file));
  assert.match(r.plain, /ctx \S+ 95% 190\.0k\/200\.0k/); // experto
  assert.ok(r.stdout.includes('\x1b[38;2;232;230;220m'), r.stdout); // templado (e8e6dc)
  assert.ok(!r.stdout.includes('\x1b[38;2;122;162;247m'), r.stdout); // no tokyo-night
  assert.doesNotMatch(r.plain, /charla larga|→|Todo bien/i);

  // mode avisos escribe quiet:false y el consejo aparece; el mensaje dice el estado real.
  const on = run({ home, mode: null, args: ['mode', 'avisos'] });
  assert.match(on.plain, /modo "experto" \(avisos, tema templado\)/);
  assert.strictEqual(JSON.parse(fs.readFileSync(file, 'utf8')).quiet, false);
  assert.match(run({ home, input, mode: null }).plain, /charla larga/);

  // mode silencio escribe quiet:true y vuelve a callar.
  const off = run({ home, mode: null, args: ['mode', 'silencio'] });
  assert.match(off.plain, /modo "experto" \(silencio, tema templado\)/);
  assert.strictEqual(JSON.parse(fs.readFileSync(file, 'utf8')).quiet, true);
  assert.doesNotMatch(run({ home, input, mode: null }).plain, /charla larga|→/);

  // STATUSLINE_MODE y STATUSLINE_THEME siguen ganandole al default.
  const env = run({ home: tempHome(), input, mode: 'normal' });
  assert.doesNotMatch(env.plain, /ctx \S+ 95%/);
  // run() borra STATUSLINE_THEME del env: aca se lanza a mano. nord: modelo 88c0d0 = 136;192;208.
  const { spawnSync } = require('node:child_process');
  const { SCRIPT } = require('./helpers');
  const h = tempHome();
  const themed = spawnSync(process.execPath, [SCRIPT], {
    input: JSON.stringify(input),
    encoding: 'utf8',
    env: { ...process.env, HOME: h, USERPROFILE: h, STATUSLINE_THEME: 'nord' },
    timeout: 20000,
  });
  assert.ok(themed.stdout.includes('\x1b[38;2;136;192;208m'), themed.stdout);
});
