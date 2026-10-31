#!/usr/bin/env node
// Status line de Claude Code con 3 modos:
//   simple  -> semaforo + una accion, en palabras llanas (sin tokens ni %)
//   normal  -> barras con etiquetas faciles + consejo si hace falta
//   experto -> todos los numeros (ctx, costo, cache, proyeccion) + consejo
// Recibe por stdin el JSON de sesion que manda Claude Code.
//
// Cambiar de modo:  node statusline.js mode simple|normal|experto
// Avisos:           node statusline.js mode silencio|avisos  (silencio = sin consejos ni etiquetas de aviso; los numeros siguen)
//   (escribe ~/.claude/fluency4d/statusline.json; se lee en cada render, sin reiniciar)
// Env opcionales:
//   STATUSLINE_MODE        modo si no hay archivo (default normal)
//   STATUSLINE_CUT_TOKENS  desde cuantos tokens la charla es "larga" (default: cutFraction del archivo, o mitad de la ventana)
//   (statusline.json puede traer "cutFraction": 0.25|0.5|0.75 = fraccion de la ventana; el env tiene prioridad)
//   STATUSLINE_THEME       tokyo-night (default) | catppuccin | nord | gruvbox | templado
//                          (tambien: node statusline.js mode <tema>, que tiene prioridad)
const fs = require('fs');
const os = require('os');
const path = require('path');

const FLAGS_DIR = path.join(os.homedir(), '.claude', 'fluency4d');
const MODE_FILE = path.join(FLAGS_DIR, 'statusline.json');
const MODES = ['simple', 'normal', 'experto'];
// Dos senales separadas (docs: platform.claude.com/docs/en/build-with-claude/prompt-caching y /context-windows):
// - COSTO del proximo mensaje: depende de la cache, no del tamano. Releer contexto cacheado cuesta 0.05x
//   (Opus/Sonnet 5.5; 0.1x en otros modelos, usamos 0.1 por conservador); si la cache esta fria se reescribe a 1.25x.
//   Sin recargo por contexto largo en modelos de 1M, asi que el tamano solo no hace caro un mensaje.
// - LARGO de la charla: aviso de calidad (context rot), no de costo. Corte = mitad de la ventana.
const CUT_ENV = Number(process.env.STATUSLINE_CUT_TOKENS) || null;
const CACHE_READ = 0.1;
// Reescribir la cache fria: 1.25x con TTL de 5 min, 2x con TTL de 1 h (prompt_cache.ttl).
const CACHE_WRITE_5M = 1.25;
const CACHE_WRITE_1H = 2;
// ttl puede venir como segundos (3600) o texto ("1h", "60m", "ephemeral_1h"): cualquier cosa >= 1 h cuenta como larga.
function ttlIsLong(ttl) {
  if (typeof ttl === 'number') return ttl >= 3600;
  if (typeof ttl !== 'string') return false;
  const m = ttl.match(/(\d+)\s*([hms])/i);
  if (!m) return /^\d+$/.test(ttl) && Number(ttl) >= 3600;
  const secs = Number(m[1]) * ({ h: 3600, m: 60, s: 1 })[m[2].toLowerCase()];
  return secs >= 3600;
}

// --- Temas (truecolor, hex) ---
const THEMES = {
  'tokyo-night': { dim: '565f89', label: '9aa5ce', text: 'c0caf5', model: '7aa2f7', accent: 'bb9af7', git: 'ff9e64', ok: '9ece6a', warn: 'e0af68', bad: 'f7768e' },
  catppuccin:    { dim: '6c7086', label: 'a6adc8', text: 'cdd6f4', model: '89b4fa', accent: 'cba6f7', git: 'fab387', ok: 'a6e3a1', warn: 'f9e2af', bad: 'f38ba8' },
  nord:          { dim: '4c566a', label: 'd8dee9', text: 'eceff4', model: '88c0d0', accent: 'b48ead', git: 'd08770', ok: 'a3be8c', warn: 'ebcb8b', bad: 'bf616a' },
  gruvbox:       { dim: '928374', label: 'bdae93', text: 'ebdbb2', model: '83a598', accent: 'd3869b', git: 'fe8019', ok: 'b8bb26', warn: 'fabd2f', bad: 'fb4934' },
  // "Acento puntual": crema + grises cálidos; el naranja de Claude (= `claude` en
  // themes/templado.json) solo en el ● de estado OK (dot). rule = separadores tenues.
  // Contrastes elegidos sobre fondo #141414.
  templado:        { dim: '8c877d', label: 'a8a49a', text: 'e8e6dc', model: 'e8e6dc', accent: 'e8e6dc', git: 'a8a49a', ok: '8aa68a', warn: 'b8a070', bad: 'bd8282', rule: '4a4640', dot: 'd97757' },
};
// Solo temas propios: `toString`, `__proto__` o `valueOf` no son temas.
const isTheme = (t) => typeof t === 'string' && Object.hasOwn(THEMES, t);
const hex = (h) => `\x1b[38;2;${parseInt(h.slice(0, 2), 16)};${parseInt(h.slice(2, 4), 16)};${parseInt(h.slice(4, 6), 16)}m`;
// statusline.json se lee una sola vez por proceso (un render o un `mode`) y se
// pasa a quien lo necesita.
const STATE = readState();
// Prioridad: /barra <tema> (archivo de estado) > STATUSLINE_THEME > tokyo-night.
const THEME = [STATE.theme, process.env.STATUSLINE_THEME].find(isTheme) || 'tokyo-night';
const palette = THEMES[THEME];
const S = { reset: '\x1b[0m', bold: '\x1b[1m' };
for (const [k, v] of Object.entries(palette)) S[k] = hex(v);

const paint = (color, s) => `${color}${s}${S.reset}`;
// Separadores: rule si el tema la define (decorativa), si no dim.
const RULE = S.rule || S.dim;
const SEP = paint(RULE, '  │  ');
const DOT = paint(S.dim, ' · ');

// Mas uso = peor (contexto, plan).
const levelUp = (p, warn = 50, bad = 80) => (p < warn ? S.ok : p < bad ? S.warn : S.bad);
// Mas = mejor (hit ratio de cache).
const levelDown = (p, warn = 90, bad = 70) => (p >= warn ? S.ok : p >= bad ? S.warn : S.bad);
// Sin emojis: un punto con el color del estado, en todos los temas.
// Con `dot` en el tema, el ● de estado OK va en ese acento; warn/bad conservan su color.
const glyph = (level) => paint(level === 'ok' && S.dot ? S.dot : S[level], '●');
const dotFor = (color) => glyph(color === S.ok ? 'ok' : color === S.warn ? 'warn' : 'bad');

function bar(pct, color, width = 10) {
  const filled = Math.max(0, Math.min(width, Math.round((pct / 100) * width)));
  return paint(color, '▰'.repeat(filled)) + paint(RULE, '▱'.repeat(width - filled));
}

function fmtTokens(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 === 0 ? 0 : 2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return String(n);
}

const hhmm = (ms) => {
  const d = new Date(ms);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}hs`;
};

// Solo un objeto plano cuenta como estado: un numero, un array o null = {} (asi
// `mode` siempre escribe un objeto valido en vez de "guardar" en un primitivo).
function readState() {
  try {
    const st = JSON.parse(fs.readFileSync(MODE_FILE, 'utf8'));
    return st && typeof st === 'object' && !Array.isArray(st) ? st : {};
  } catch { return {}; } // sin archivo = default
}

// Texto de stdin o de archivos: sin caracteres de control (ESC, CR, BEL...) que
// rompan o falsifiquen la barra. No-string = null.
const clean = (s) => (typeof s === 'string' ? s.replace(/[\x00-\x1f\x7f-\x9f]/g, '') : null);
// Numero finito (los strings numericos se convierten); cualquier otra cosa = null.
function num(v) {
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
}
// Epoch en segundos (> 1e11 se toma como ms); fuera de rango = null.
function epochSec(v) {
  let n = num(v);
  if (n === null || n <= 0) return null;
  if (n > 1e11) n /= 1000;
  return n < 1e10 ? n : null;
}
// Suma de tokens de un `usage`; null si ningun campo es un numero valido.
function sumTokens(u) {
  const parts = [u.input_tokens, u.cache_read_input_tokens, u.cache_creation_input_tokens].map(num).filter((n) => n !== null && n >= 0);
  return parts.length ? parts.reduce((a, b) => a + b, 0) : null;
}

function readMode(st) {
  if (MODES.includes(st.mode)) return st.mode;
  return MODES.includes(process.env.STATUSLINE_MODE) ? process.env.STATUSLINE_MODE : 'normal';
}

// Fraccion de la ventana para "charla larga": cutFraction del archivo (0 < f < 1), si no la mitad.
function cutFraction(st) {
  const f = Number(st.cutFraction);
  return f > 0 && f < 1 ? f : 0.5;
}

// Fallback si el JSON no trae context_window: ultimo turno del hilo principal.
function contextFromTranscript(file) {
  if (typeof file !== 'string' || !file) return null;
  try { return readTranscriptTail(file); } catch { return null; } // ilegible o no es un archivo
}

function readTranscriptTail(file) {
  if (!fs.existsSync(file)) return null;
  const size = fs.statSync(file).size;
  const len = Math.min(size, 512 * 1024);
  const buf = Buffer.alloc(len);
  const fd = fs.openSync(file, 'r');
  fs.readSync(fd, buf, 0, len, size - len);
  fs.closeSync(fd);
  const lines = buf.toString('utf8').split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const e = JSON.parse(lines[i]);
      const u = e.message && e.message.usage;
      if (!u || typeof u !== 'object' || e.isSidechain) continue;
      const n = sumTokens(u);
      if (n !== null) return n;
    } catch { /* linea cortada o no-JSON */ }
  }
  return null;
}

// HEAD real de un dir: `.git` carpeta (repo normal) o `.git` archivo con
// `gitdir: <ruta>` (worktree o submodulo; la ruta puede ser relativa al dir).
// undefined = no hay `.git` aca (seguir subiendo); null = hay `.git` pero no
// resuelve (gitdir roto, tipo raro): el repo es este y no tiene rama legible.
function gitHeadPath(d) {
  const dotgit = path.join(d, '.git');
  let st;
  try { st = fs.statSync(dotgit); } catch { return undefined; }
  if (st.isDirectory()) return path.join(dotgit, 'HEAD');
  if (!st.isFile()) return null;
  try {
    const m = fs.readFileSync(dotgit, 'utf8').match(/^gitdir:\s*(.+?)\s*$/m);
    if (!m || isUnc(m[1])) return null;
    const head = path.join(path.resolve(d, m[1]), 'HEAD');
    return isUnc(head) ? null : head;
  } catch { return null; }
}

// Ruta de red (\\host\share o //host/share): en Windows abrirla en cada render
// intenta una conexion SMB y filtra el hash NTLM. Un gitdir asi no se sigue.
const isUnc = (p) => /^[\\/]{2}/.test(p);

function gitBranch(dir) {
  if (typeof dir !== 'string' || !dir) return null;
  try {
    return findBranch(dir);
  } catch { return null; } // HEAD carpeta (EISDIR), permisos, etc.
}

function findBranch(dir) {
  let d = dir;
  for (let i = 0; d && i < 25; i++) {
    const head = gitHeadPath(d);
    if (head !== undefined) {
      // Hay `.git`: este es el repo; si HEAD no resuelve no se sigue subiendo.
      if (!head || !fs.existsSync(head)) return null;
      const ref = fs.readFileSync(head, 'utf8').trim();
      return clean(ref.startsWith('ref: ') ? ref.replace('ref: refs/heads/', '') : ref.slice(0, 7)) || null;
    }
    const parent = path.dirname(d);
    if (parent === d) break;
    d = parent;
  }
  return null;
}

// Modos opt-in de fluency-4d: flags globales en ~/.claude/fluency4d/<modo>.json ({"on": true, "level": ...}).
// Paridad con los hooks: la barra muestra un modo SOLO si el hook lo aplicaria.
// - hook_utils.load_adhd / load_caveman: objeto JSON, on === true y level en el set.
// - hook_utils.load_verify: objeto JSON y on === true (sin level).
// - adhd_injector: ADHD cede ante caveman (si caveman esta activo, ADHD no se aplica).
// Casos compartidos con pytest: tests/fluency-4d/fixtures/flags_parity.json.
const ADHD_LEVELS = ['auto', 'lite', 'full'];
const CAVEMAN_LEVELS = ['auto', 'lite', 'full', 'ultra'];

function readFlag(name) {
  try {
    const st = JSON.parse(fs.readFileSync(path.join(FLAGS_DIR, `${name}.json`), 'utf8'));
    return st && typeof st === 'object' && !Array.isArray(st) && st.on === true ? st : null;
  } catch { return null; } // flag ausente o invalido = apagado
}

function fluencyModes() {
  const withLevel = (label, level) => (level !== 'auto' ? `${label}:${level}` : label);
  const caveman = readFlag('caveman');
  const cavemanOn = !!caveman && CAVEMAN_LEVELS.includes(caveman.level);
  const adhd = readFlag('adhd');
  const adhdOn = !cavemanOn && !!adhd && ADHD_LEVELS.includes(adhd.level);
  const on = [];
  if (adhdOn) on.push(withLevel('ADHD', adhd.level));
  if (cavemanOn) on.push(withLevel('caveman', caveman.level));
  if (readFlag('verify')) on.push('verify');
  return on;
}

// Escritura atomica: tmp en el mismo dir + rename (un render concurrente nunca lee un JSON a medias).
// En Windows el rename falla con EPERM/EBUSY/EACCES si otro proceso tiene el
// destino abierto: se reintenta 5 veces con una espera corta y sincrona.
const RENAME_RETRY = new Set(['EPERM', 'EBUSY', 'EACCES']);
const sleepMs = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
function renameRetry(from, to) {
  for (let i = 0; ; i++) {
    try { return fs.renameSync(from, to); } catch (e) {
      if (i >= 4 || !RENAME_RETRY.has(e && e.code)) throw e;
      sleepMs(10 * 2 ** i); // 10, 20, 40, 80 ms
    }
  }
}

function atomicWriteJson(file, obj) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  try {
    fs.writeFileSync(tmp, JSON.stringify(obj) + '\n');
    renameRetry(tmp, file);
  } catch (e) {
    try { fs.unlinkSync(tmp); } catch { /* ya no existe */ }
    throw e;
  }
}

// Proyeccion lineal del uso de 5h: si al ritmo actual se llega al 100% antes del reset, devuelve esa hora (ms).
function projectCap(usedPct, resetsAtSec) {
  const now = Date.now();
  const resetMs = resetsAtSec * 1000;
  const elapsed = now - (resetMs - 5 * 3600 * 1000);
  if (usedPct < 10 || usedPct >= 100 || elapsed < 15 * 60 * 1000) return null; // muy temprano = ruido
  const capMs = now + ((100 - usedPct) / usedPct) * elapsed;
  return capMs < resetMs ? capMs : null;
}

// --- Datos normalizados (una sola vez, los usan los 3 modos) ---
const isObj = (v) => !!v && typeof v === 'object' && !Array.isArray(v);

// Un limite del plan con porcentaje finito (0..1000) y resets_at valido o null.
function limit(v) {
  if (!isObj(v)) return null;
  const p = typeof v.used_percentage === 'number' && Number.isFinite(v.used_percentage) ? v.used_percentage : null;
  if (p === null || p < 0 || p > 1000) return null;
  return { used_percentage: p, resets_at: epochSec(v.resets_at) };
}

function collect(s) {
  if (!isObj(s)) s = {};
  const m = isObj(s.model) ? s.model : {};
  const model = clean(m.display_name) || clean(m.id) || 'Claude';
  const modelId = clean(m.id) || '';
  const cw = isObj(s.context_window) ? s.context_window : {};
  const size = num(cw.context_window_size);
  const windowSize = size !== null && size > 0 ? size : (/\[1m\]|1M/i.test(modelId + model) ? 1_000_000 : 200_000);
  let used = isObj(cw.current_usage) ? sumTokens(cw.current_usage) : null;
  if (used === null) used = contextFromTranscript(s.transcript_path);

  const rl = isObj(s.rate_limits) ? s.rate_limits : {};
  const five = limit(rl.five_hour);
  const week = limit(rl.seven_day);

  const pc = isObj(s.prompt_cache) ? s.prompt_cache : null;
  const ratio = pc ? num(pc.hit_ratio) : null;
  const hit = ratio !== null && ratio >= 0 && ratio <= 1 ? Math.round(ratio * 100) : null;
  const expires = pc ? epochSec(pc.expires_at) : null;
  const minsLeft = expires !== null ? Math.floor((expires * 1000 - Date.now()) / 60000) : null;
  const cold = !!pc && (pc.warm === false || (minsLeft !== null && minsLeft <= 0));
  let missCause = pc ? clean(pc.last_miss_cause) : null;
  if (!missCause && pc && isObj(pc.miss_causes)) {
    missCause = clean(Object.entries(pc.miss_causes).sort((a, b) => (num(b[1]) || 0) - (num(a[1]) || 0)).map(([k]) => k)[0]);
  }
  const cost = isObj(s.cost) ? num(s.cost.total_cost_usd) : null;
  const recache = pc ? num(pc.recache_tokens_if_cold) : null;
  const ws = isObj(s.workspace) ? s.workspace.current_dir : undefined;

  return {
    model, effort: isObj(s.effort) ? clean(s.effort.level) : null, fast: !!s.fast_mode, thinking: !!(isObj(s.thinking) && s.thinking.enabled),
    used, windowSize, cut: CUT_ENV || Math.round(windowSize * cutFraction(STATE)), pct: used !== null ? Math.round((used / windowSize) * 100) : null,
    cost,
    branch: gitBranch(typeof ws === 'string' && ws ? ws : typeof s.cwd === 'string' ? s.cwd : null),
    modes: fluencyModes(),
    five, week, cap: five && five.resets_at ? projectCap(five.used_percentage, five.resets_at) : null,
    pc, hit, minsLeft, cold, missCause, recache: recache !== null && recache > 0 ? recache : null, ttlLong: !!pc && ttlIsLong(pc.ttl),
  };
}

// Cuanto gasta el proximo mensaje solo por releer el contexto (en tokens de input equivalentes), en palabras.
function spend(d) {
  if (d.used === null) return null;
  const eq = d.used * (d.cold ? (d.ttlLong ? CACHE_WRITE_1H : CACHE_WRITE_5M) : CACHE_READ);
  if (eq < 25_000) return { word: 'poco', color: S.ok };
  if (eq < 100_000) return { word: 'medio', color: S.warn };
  return { word: 'mucho', color: S.bad };
}

// El consejo mas urgente, en castellano llano: { level: ok|warn|bad, msg, action? }.
// skipHeavy: el modo experto ya marca la charla larga con su etiqueta.
function advice(d, { skipHeavy = false } = {}) {
  const reset = d.five && d.five.resets_at ? hhmm(d.five.resets_at * 1000) : null;
  if (d.cap) {
    return { level: 'bad', msg: `Al ritmo actual te quedás sin plan a las ${hhmm(d.cap)}${reset ? ` (vuelve a las ${reset})` : ''}`,
      action: 'Bajá el ritmo o pasá a un modelo más liviano (/model)' };
  }
  if (d.five && d.five.used_percentage >= 90) {
    return { level: 'bad', msg: `Casi sin plan por ahora${reset ? ` (vuelve a las ${reset})` : ''}`, action: 'Guardalo para lo importante' };
  }
  if (d.week && d.week.used_percentage >= 90) {
    return { level: 'bad', msg: 'Casi sin plan para esta semana', action: 'Guardalo para lo importante' };
  }
  if (d.cold) {
    return { level: 'warn', msg: 'Volviste de una pausa: el próximo mensaje gasta más de lo normal',
      action: 'Si cambiás de tema, mejor un chat nuevo (/clear)' };
  }
  if (!skipHeavy && d.used !== null && d.used >= d.cut) {
    return { level: 'warn', msg: 'Charla larga: con tanto contexto el modelo rinde peor',
      action: 'Si cambiás de tema, empezá un chat nuevo (/clear)' };
  }
  if (d.minsLeft !== null && d.minsLeft < 5) {
    return { level: 'warn', msg: `Si vas a seguir, escribí en los próximos ${Math.max(d.minsLeft, 1)} min`,
      action: 'Después, el próximo mensaje gasta más' };
  }
  if (d.hit !== null && d.hit < 70) {
    return { level: 'warn', msg: 'Algo cambió (p. ej. el modelo) y se perdió el ahorro',
      action: 'Evitá cambiar de modelo o de herramientas a mitad de charla' };
  }
  if (d.five && d.five.used_percentage >= 75) {
    return { level: 'warn', msg: `Te queda poco plan${reset ? ` hasta las ${reset}` : ''}` };
  }
  return { level: 'ok', msg: 'Todo bien' };
}

const LEVEL = { ok: [glyph('ok'), () => S.ok], warn: [glyph('warn'), () => S.warn], bad: [glyph('bad'), () => S.bad] };

const QUIET = STATE.quiet === true;

function adviceLines(a, { withOk }) {
  if (QUIET || (a.level === 'ok' && !withOk)) return [];
  const [icon, col] = LEVEL[a.level];
  const lines = [`${icon} ${paint(col(), a.msg)}`];
  if (a.action) lines.push(`   ${paint(S.dim, '→')} ${paint(S.text, a.action)}`);
  return lines;
}

// --- Modo simple: semaforo + accion ---
function renderSimple(d) {
  const a = advice(d);
  if (a.level !== 'ok' && !QUIET) return adviceLines(a, { withOk: true });
  const parts = QUIET ? [] : [`${glyph('ok')} ${paint(S.ok, 'Todo bien')}`];
  if (d.five) {
    const p = d.five.used_percentage; // con silencio esta linea se ve aunque el plan este alto
    parts.push(`${paint(S.label, 'Plan:')} ${p >= 75 ? paint(S.warn, 'queda poco') : paint(S.text, 'te alcanza')}`);
  }
  const sp = spend(d);
  if (sp) parts.push(`${paint(S.label, 'Cada mensaje gasta:')} ${paint(sp.color, sp.word)}`);
  return [parts.join(DOT)];
}

// --- Modo normal: barras con etiquetas faciles ---
function renderNormal(d) {
  let head = paint(S.model + S.bold, `◆ ${d.model}`);
  if (d.effort) head += DOT + paint(S.text, d.effort);
  const parts = [head];

  if (d.pct !== null) {
    const sp = spend(d);
    // La barra mide el "peso" de la charla: llena = umbral de charla pesada, no la ventana entera.
    const weight = Math.min(100, Math.round((d.used / d.cut) * 100));
    parts.push(`${paint(S.label, 'charla')} ${bar(weight, sp.color, 6)} ${paint(S.label, 'cada msg gasta')} ${paint(sp.color, sp.word)}`);
  }
  const plan = [];
  if (d.five) {
    const p = d.five.used_percentage;
    let seg = `${paint(S.label, 'plan')} ${bar(p, levelUp(p, 50, 75), 6)} ${paint(levelUp(p, 50, 75), `${p}%`)}`;
    if (d.five.resets_at) seg += ' ' + paint(S.dim, `(vuelve ${hhmm(d.five.resets_at * 1000)})`);
    plan.push(seg);
  }
  if (d.week) plan.push(`${paint(S.label, 'semana')} ${paint(levelUp(d.week.used_percentage, 50, 75), `${d.week.used_percentage}%`)}`);
  if (plan.length) parts.push(plan.join(DOT));
  if (d.modes.length) parts.push(`${paint(S.dim, '4D')} ${paint(S.accent, d.modes.join(' '))}`);

  return [parts.join(SEP), ...adviceLines(advice(d), { withOk: false })];
}

// --- Modo experto: todos los numeros ---
function renderExpert(d) {
  let head = paint(S.model + S.bold, `◆ ${d.model}`);
  if (d.effort) head += DOT + paint(S.text, d.effort);
  if (d.fast) head += ' ' + paint(S.warn, 'fast');
  if (d.thinking) head += ' ' + paint(S.label, '✻');
  const one = [head];

  if (d.pct !== null) {
    // Amarillo desde el corte de charla larga (coincide con la etiqueta), rojo cerca del auto-compact.
    const col = d.pct >= 80 ? S.bad : d.used >= d.cut ? S.warn : S.ok;
    let ctx = `${paint(S.label, 'ctx')} ${bar(d.pct, col)} ${paint(col, `${d.pct}%`)} ${paint(S.dim, `${fmtTokens(d.used)}/${fmtTokens(d.windowSize)}`)}`;
    if (!QUIET && d.used >= d.cut) ctx += ' ' + paint(S.warn, 'charla larga');
    one.push(ctx);
  } else {
    one.push(`${paint(S.label, 'ctx')} ${paint(S.dim, '—')}`);
  }
  if (typeof d.cost === 'number') one.push(`${paint(S.text, `$${d.cost.toFixed(2)}`)} ${paint(S.dim, 'sesión')}`);
  if (d.branch) one.push(paint(S.git, `⎇ ${d.branch}`));
  if (d.modes.length) one.push(`${paint(S.dim, '4D')} ${paint(S.accent, d.modes.join(' '))}`);

  const two = [];
  const plan = [];
  if (d.five) {
    const p = d.five.used_percentage;
    let seg = `${paint(S.label, '5h')} ${bar(p, levelUp(p), 8)} ${paint(levelUp(p), `${p}%`)}`;
    if (d.five.resets_at) seg += ' ' + paint(S.dim, `vuelve ${hhmm(d.five.resets_at * 1000)}`);
    if (!QUIET && d.cap) seg += ' ' + paint(S.bad + S.bold, `tope ~${hhmm(d.cap)}`);
    plan.push(seg);
  }
  if (d.week) plan.push(`${paint(S.label, '7d')} ${bar(d.week.used_percentage, levelUp(d.week.used_percentage), 8)} ${paint(levelUp(d.week.used_percentage), `${d.week.used_percentage}%`)}`);
  if (plan.length) two.push(`${paint(S.label, 'plan')}  ${plan.join(DOT)}`);

  if (d.pc) {
    const segs = [];
    if (d.cold) {
      // Fría: primero lo que importa ahora (la recarga); el reciclado queda como dato anterior.
      const mult = d.ttlLong ? '2x' : '1.25x';
      segs.push(`${dotFor(S.bad)} ${paint(S.bad, 'fría')}`);
      if (d.recache) segs.push(paint(S.bad, `el próximo msg recarga ${fmtTokens(d.recache)} (${mult})`));
      if (d.hit !== null) segs.push(paint(S.dim, `antes reciclaba ${d.hit}%`));
    } else if (d.hit !== null) {
      const col = levelDown(d.hit);
      let seg = `${dotFor(col)} ${paint(S.label, 'reciclado')} ${paint(col, `${d.hit}%`)}`;
      if (col !== S.ok && d.missCause) seg += ' ' + paint(S.dim, `(${String(d.missCause).replace(/_/g, ' ')})`);
      segs.push(seg);
    }
    if (!d.cold && d.minsLeft !== null) {
      const col = d.minsLeft < 5 ? S.bad : d.minsLeft < 15 ? S.warn : S.ok;
      segs.push(`${paint(S.label, 'vence en')} ${paint(col, `${d.minsLeft}m`)}${!QUIET && d.minsLeft < 5 ? ' ' + paint(S.bad + S.bold, '!') : ''}`);
    }
    if (segs.length) two.push(`${paint(S.label, 'caché')}  ${segs.join(DOT)}`);
  }

  return [one.join(SEP), two.join(SEP), ...adviceLines(advice(d, { skipHeavy: true }), { withOk: false })].filter(Boolean);
}

const RENDER = { simple: renderSimple, normal: renderNormal, experto: renderExpert };

// CLI: node statusline.js mode <simple|normal|experto>
if (process.argv[2] === 'mode') {
  const m = process.argv[3];
  const st = STATE;
  const avisos = () => (st.quiet === true ? 'silencio' : 'avisos');
  if (m === 'silencio' || m === 'avisos') {
    st.quiet = m === 'silencio';
  } else if (MODES.includes(m)) {
    st.mode = m;
  } else if (isTheme(m)) {
    st.theme = m;
  } else {
    console.log(`Modo actual: ${readMode(st)} (${avisos()}, tema ${clean(st.theme) || THEME}). Uso: node statusline.js mode ${MODES.join('|')}|silencio|avisos|<tema: ${Object.keys(THEMES).join(', ')}>`);
    process.exit(m ? 1 : 0);
  }
  try {
    atomicWriteJson(MODE_FILE, st);
  } catch (e) {
    // Sin stack trace: un mensaje claro y exit != 0 (el .tmp ya se borro).
    console.error(`No pude guardar ${MODE_FILE}: ${(e && e.code) || (e && e.message) || e}. Proba de nuevo.`);
    process.exit(1);
  }
  console.log(`Status line en modo "${readMode(st)}" (${avisos()}, tema ${isTheme(st.theme) ? st.theme : THEME}).`);
  process.exit(0);
}

// Render con lo que llego; si stdin no cierra en 2 s se pinta igual y se sale.
let input = '';
let done = false;
function render() {
  if (done) return;
  done = true;
  let s = {};
  try { s = (JSON.parse(input) || {}); } catch { /* sin datos o cortado */ }
  process.stdout.write(RENDER[readMode(STATE)](collect(s)).join('\n'), () => process.exit(0));
}
const STDIN_TIMEOUT_MS = 2000;
setTimeout(render, STDIN_TIMEOUT_MS).unref();
// Decodifica el stream entero: un caracter multibyte partido entre dos chunks no
// sale como U+FFFD.
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => (input += c));
process.stdin.on('end', render);
process.stdin.on('error', render);
