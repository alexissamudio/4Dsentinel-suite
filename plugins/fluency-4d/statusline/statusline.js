#!/usr/bin/env node
// Status line de Claude Code (parte de fluency-4d) con 3 modos:
//   simple  -> semaforo + una accion, en palabras llanas (sin tokens ni %)
//   normal  -> barras con etiquetas faciles + consejo si hace falta
//   experto -> todos los numeros (ctx, costo, cache, proyeccion) + consejo
//
// Como se invoca: `/statusline setup` copia este archivo a la ruta fija
// ~/.claude/fluency4d/statusline.js y pone `statusLine` en settings.json. Claude
// Code lo corre como proceso nuevo en cada refresco (eventos + refreshInterval),
// le manda por stdin el JSON de la sesion (modelo, context_window, rate_limits,
// prompt_cache, cost, workspace...) y pinta cada linea de stdout como una fila.
//
// Lee (nunca escribe al renderizar): ~/.claude/fluency4d/statusline.json (modo,
// tema, avisos, cutFraction), los flags adhd/caveman/verify.json del mismo dir,
// la cola del transcript (solo si el JSON no trae el uso de contexto) y el HEAD
// de git del dir de trabajo. Escribe solo statusline.json, y solo con `mode`.
//
// Cambiar de modo:  node statusline.js mode simple|normal|experto
// Avisos:           node statusline.js mode silencio|avisos  (silencio = sin consejos ni etiquetas de aviso; los numeros siguen; default silencio)
//   (escribe ~/.claude/fluency4d/statusline.json; se lee en cada render, sin reiniciar)
// Env opcionales:
//   STATUSLINE_MODE        modo si no hay archivo (default experto)
//   STATUSLINE_CUT_TOKENS  desde cuantos tokens la charla es "larga" (default: cutFraction del archivo, o mitad de la ventana)
//   (statusline.json puede traer "cutFraction": 0.25|0.5|0.75 = fraccion de la ventana; el env tiene prioridad)
//   STATUSLINE_THEME       templado (default) | tokyo-night | catppuccin | nord | gruvbox
//                          (tambien: node statusline.js mode <tema>, que tiene prioridad)
// Defaults (experto, silencio, templado): los mismos que asume el Panel 4D
// (hooks/register.tsx) y la skill /barra; si divergen, el panel mostraria un
// valor "actual" que la barra no aplica. Experto: la vista completa (simple y
// normal son recortes que se eligen). Silencio: los consejos son opt-in
// (`mode avisos`) y los numeros se ven igual. Templado: el tema del propio
// plugin, a juego con themes/templado.json.
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
// Solo un numero finito > 0: num() descarta "", "abc", "Infinity" y "1e400"; 0 y negativos tambien quedan afuera.
const CUT_ENV = ((n) => (n !== null && n > 0 ? n : null))(num(process.env.STATUSLINE_CUT_TOKENS));
const CACHE_READ = 0.1;
// Tope de cordura para un conteo de tokens del stdin o del transcript (ventanas
// reales: <= ~1e7). Lo que pase de aca se descarta como dato invalido.
const MAX_TOKENS = 1e9;
// Reescribir la cache fria: 1.25x con TTL de 5 min, 2x con TTL de 1 h (prompt_cache.ttl).
const CACHE_WRITE_5M = 1.25;
const CACHE_WRITE_1H = 2;
/**
 * Si el TTL de la cache es largo (>= 1 h), lo que sube el costo de reescribirla.
 * ttl puede venir como segundos (3600) o texto ("1h", "60m", "ephemeral_1h").
 * @param {unknown} ttl prompt_cache.ttl tal como llega
 * @returns {boolean} false si no se puede interpretar
 */
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
/**
 * Si `t` es el nombre de un tema de THEMES. Solo claves propias: `toString`,
 * `__proto__` o `valueOf` (heredadas de Object) no son temas.
 * @param {unknown} t
 * @returns {boolean}
 */
const isTheme = (t) => typeof t === 'string' && Object.hasOwn(THEMES, t);
const hex = (h) => `\x1b[38;2;${parseInt(h.slice(0, 2), 16)};${parseInt(h.slice(2, 4), 16)};${parseInt(h.slice(4, 6), 16)}m`;
// statusline.json se lee una sola vez por proceso (un render o un `mode`) y se
// pasa a quien lo necesita.
const STATE = readState();
// Prioridad: /barra <tema> (archivo de estado) > STATUSLINE_THEME > templado.
const THEME = [STATE.theme, process.env.STATUSLINE_THEME].find(isTheme) || 'templado';
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

/**
 * Tokens en corto: < 1000 redondeado a entero, k con 1 decimal, M exacto sin
 * decimales ("1M") y M no exacto con 2 ("1.50M"). Lo que en k redondearia a
 * "1000.0k" (999_950..999_999) sube a "1.00M"; igual 1_004_999 -> "1.00M": solo
 * un multiplo exacto de 1M va sin decimales. Fuera de dominio (no number, NaN,
 * Infinity, negativo, o un texto de mas de 8 caracteres o con notacion
 * cientifica, p. ej. >= 1e10) = "—".
 * Mismo cuerpo que fmtTokens de hooks/register.tsx (paridad exacta:
 * test/fmt_tokens_parity.test.js).
 * @param {unknown} n
 * @returns {string} a lo sumo 8 caracteres
 */
function fmtTokens(n) {
  if (typeof n !== 'number' || !Number.isFinite(n) || n < 0) return '—';
  const k = (n / 1e3).toFixed(1);
  let s;
  if (n < 999.5) s = String(Math.round(n));
  else if (n < 1e6 && k !== '1000.0') s = k + 'k';
  else s = (n / 1e6).toFixed(n % 1e6 === 0 ? 0 : 2) + 'M';
  return s.length <= 8 && /^\d+(\.\d+)?[kM]?$/.test(s) ? s : '—';
}

const hhmm = (ms) => {
  const d = new Date(ms);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}hs`;
};

/**
 * JSON.parse sin el BOM UTF-8 inicial (lo agregan Notepad o PowerShell 5 con
 * `-Encoding utf8`; readFileSync 'utf8' no lo saca y JSON.parse lo rechaza).
 * Lo usan todas las lecturas de JSON de la barra: statusline.json, los flags,
 * las lineas del transcript y el stdin. Es declaracion de funcion (hoisted)
 * porque readState() corre antes de esta linea.
 * @param {string} text
 * @returns {unknown}
 * @throws SyntaxError si no es JSON
 */
function parseJson(text) {
  return JSON.parse(text.charCodeAt(0) === 0xfeff ? text.slice(1) : text);
}

/**
 * Lee ~/.claude/fluency4d/statusline.json (con o sin BOM). Solo un objeto plano
 * cuenta como estado: un numero, un array o null = {} (asi `mode` siempre escribe
 * un objeto valido en vez de "guardar" en un primitivo). Cada clave se valida
 * donde se usa (isTheme, MODES, quiet === false, cutFraction via num()).
 * @returns {object} el estado, o {} si falta, es ilegible o no es un objeto
 */
function readState() {
  try {
    const st = parseJson(fs.readFileSync(MODE_FILE, 'utf8'));
    return st && typeof st === 'object' && !Array.isArray(st) ? st : {};
  } catch { return {}; } // sin archivo = default
}

/**
 * Sanea texto de stdin o de archivos: saca los caracteres de control C0/C1
 * (ESC, CR, BEL...) que rompan o falsifiquen la barra con secuencias ANSI.
 * @param {unknown} s
 * @returns {string|null} el texto limpio; null si no es string
 */
const clean = (s) => (typeof s === 'string' ? s.replace(/[\x00-\x1f\x7f-\x9f]/g, '') : null);
/**
 * Numero finito (los strings numericos se convierten; "" no cuenta como 0).
 * @param {unknown} v
 * @returns {number|null} cualquier otra cosa (NaN, Infinity, objetos) = null
 */
function num(v) {
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
}
/**
 * Normaliza un epoch a segundos: un valor > 1e11 se toma como milisegundos.
 * @param {unknown} v
 * @returns {number|null} null si no es numero, es <= 0 o queda fuera de rango (>= 1e10 s)
 */
function epochSec(v) {
  let n = num(v);
  if (n === null || n <= 0) return null;
  if (n > 1e11) n /= 1000;
  return n < 1e10 ? n : null;
}
/**
 * Tokens de contexto de un `usage`: input + cache_read + cache_creation (los
 * campos invalidos, negativos o mayores que MAX_TOKENS se ignoran: un 1e308
 * haria la suma Infinity y el % saldria en notacion cientifica).
 * @param {object} u objeto usage de la API
 * @returns {number|null} null si ningun campo es un numero valido
 */
function sumTokens(u) {
  const parts = [u.input_tokens, u.cache_read_input_tokens, u.cache_creation_input_tokens].map(num).filter((n) => n !== null && n >= 0 && n <= MAX_TOKENS);
  return parts.length ? parts.reduce((a, b) => a + b, 0) : null;
}

// Modo activo: el del archivo > STATUSLINE_MODE > experto.
function readMode(st) {
  if (MODES.includes(st.mode)) return st.mode;
  return MODES.includes(process.env.STATUSLINE_MODE) ? process.env.STATUSLINE_MODE : 'experto';
}

// Fraccion de la ventana para "charla larga": cutFraction del archivo (0 < f < 1), si no la mitad.
// Solo un number o un string numerico (via num): nunca Number() sobre un objeto,
// que llama a su toString/valueOf y con {"toString":[]} tira TypeError.
function cutFraction(st) {
  const f = num(st.cutFraction);
  return f !== null && f > 0 && f < 1 ? f : 0.5;
}

// Fallback si el JSON no trae context_window: ultimo turno del hilo principal.
function contextFromTranscript(file) {
  if (typeof file !== 'string' || !file) return null;
  try { return readTranscriptTail(file); } catch { return null; } // ilegible o no es un archivo
}

// Lee solo los ultimos 512 KB (el transcript puede pesar decenas de MB y esto
// corre en cada refresco) y busca de atras para adelante el ultimo `usage` que
// no sea de un subagente (isSidechain).
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
      const e = parseJson(lines[i]);
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
    // UNC se chequea dos veces: el gitdir escrito puede ser UNC, y uno relativo
    // queda UNC al resolverse contra un `d` que ya vive en un share de red.
    if (!m || isUnc(m[1])) return null;
    const head = path.join(path.resolve(d, m[1]), 'HEAD');
    return isUnc(head) ? null : head;
  } catch { return null; }
}

// Ruta de red (\\host\share o //host/share): en Windows abrirla en cada render
// intenta una conexion SMB y filtra el hash NTLM. Un gitdir asi no se sigue:
// un `.git` archivo plantado en un repo clonado bastaria para apuntar a un host
// del atacante sin que el usuario corra nada.
const isUnc = (p) => /^[\\/]{2}/.test(p);

/**
 * Rama de git del dir (o de su repo mas cercano hacia arriba, hasta 25 niveles).
 * @param {unknown} dir workspace.current_dir o cwd del JSON de sesion
 * @returns {string|null} la rama, el sha corto si HEAD esta detached, o null si
 *   no hay repo, no se puede leer o el `.git` no resuelve
 */
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
//   Los dos piden estilos opuestos (pasos completos vs. minimo de texto); si los
//   dos flags quedan en on (p. ej. editados a mano), gana el ahorro de tokens y
//   la barra no muestra un ADHD que el hook no inyecta.
// Casos compartidos con pytest: tests/fluency-4d/fixtures/flags_parity.json.
const ADHD_LEVELS = ['auto', 'lite', 'full'];
const CAVEMAN_LEVELS = ['auto', 'lite', 'full', 'ultra'];

/**
 * Lee el flag ~/.claude/fluency4d/<name>.json, con o sin BOM: el panel
 * (parseJson) y hook_utils (read_json_safe, utf-8-sig) tambien lo toleran, asi
 * un flag con BOM da el mismo veredicto en los tres lados.
 * @param {'adhd'|'caveman'|'verify'} name
 * @returns {object|null} el objeto si es JSON valido con on === true; si no, null (apagado)
 */
function readFlag(name) {
  try {
    const st = parseJson(fs.readFileSync(path.join(FLAGS_DIR, `${name}.json`), 'utf8'));
    return st && typeof st === 'object' && !Array.isArray(st) && st.on === true ? st : null;
  } catch { return null; } // flag ausente o invalido = apagado
}

/**
 * Modos de fluency-4d que los hooks aplicarian ahora, para la etiqueta "4D".
 * @returns {string[]} p. ej. ['caveman:full', 'verify']; el nivel `auto` no se muestra
 */
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
// Pasa seguido: la barra se re-ejecuta cada pocos segundos y lee justo este
// archivo, y antivirus/indexador lo abren al cambiar. El handle dura
// milisegundos, asi que reintentar alcanza; fallar seria perder un `/barra`.
// Atomics.wait duerme sin event loop (todo aca es sincrono) y sin busy-wait.
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

/**
 * Escribe `obj` como JSON en `file` de forma atomica (tmp + rename con reintento).
 * El tmp lleva pid + hora para que dos `mode` simultaneos no compartan archivo.
 * @param {string} file ruta destino (crea la carpeta si falta)
 * @param {object} obj
 * @throws el error de escritura o de rename, despues de borrar el tmp
 */
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

/**
 * Normaliza el JSON de sesion de stdin a los datos que usan los 3 render. Todo
 * campo se valida (tipo y rango): un JSON parcial, viejo o malicioso nunca tira,
 * solo deja ese dato en null.
 * @param {unknown} s JSON de sesion parseado (cualquier cosa no-objeto = {})
 * @returns {object} model/effort/fast/thinking, uso de contexto (used, windowSize,
 *   cut, pct), cost, branch, modes, limites del plan (five, week, cap) y cache
 *   (pc, hit, minsLeft, cold, missCause, recache, ttlLong)
 */
function collect(s) {
  if (!isObj(s)) s = {};
  const m = isObj(s.model) ? s.model : {};
  const model = clean(m.display_name) || clean(m.id) || 'Claude';
  const modelId = clean(m.id) || '';
  const cw = isObj(s.context_window) ? s.context_window : {};
  const size = num(cw.context_window_size);
  // 1..MAX_TOKENS: una ventana de 1e-300 o 1e308 daria un % Infinity o 0 sin sentido.
  const windowSize = size !== null && size >= 1 && size <= MAX_TOKENS ? size : (/\[1m\]|1M/i.test(modelId + model) ? 1_000_000 : 200_000);
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
  // 0 <= costo < 1e9: toFixed(2) de un numero >= 1e21 sale en notacion cientifica.
  const rawCost = isObj(s.cost) ? num(s.cost.total_cost_usd) : null;
  const cost = rawCost !== null && rawCost >= 0 && rawCost < 1e9 ? rawCost : null;
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

/**
 * Cuanto gasta el proximo mensaje solo por releer el contexto (en tokens de
 * input equivalentes), en palabras: poco < 25k <= medio < 100k <= mucho.
 * @param {object} d datos de collect()
 * @returns {{word: string, color: string}|null} null si no se conoce el uso de contexto
 */
function spend(d) {
  if (d.used === null) return null;
  const eq = d.used * (d.cold ? (d.ttlLong ? CACHE_WRITE_1H : CACHE_WRITE_5M) : CACHE_READ);
  if (eq < 25_000) return { word: 'poco', color: S.ok };
  if (eq < 100_000) return { word: 'medio', color: S.warn };
  return { word: 'mucho', color: S.bad };
}

/**
 * El consejo mas urgente, en castellano llano. El orden de los `if` es la
 * prioridad: primero el plan (bad), despues cache fria, charla larga, cache por
 * vencer, hit ratio bajo y plan al 75% (warn).
 * @param {object} d datos de collect()
 * @param {{skipHeavy?: boolean}} [opts] skipHeavy: el modo experto ya marca la
 *   charla larga con su etiqueta
 * @returns {{level: 'ok'|'warn'|'bad', msg: string, action?: string}}
 */
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

// Silencio por default: los avisos se ven solo con quiet:false (`mode avisos`).
const QUIET = STATE.quiet !== false;

// Lineas del consejo (icono + mensaje, y "→ accion" debajo). En silencio, o si
// es "Todo bien" y no se pide withOk, ninguna.
function adviceLines(a, { withOk }) {
  if (QUIET || (a.level === 'ok' && !withOk)) return [];
  const [icon, col] = LEVEL[a.level];
  const lines = [`${icon} ${paint(col(), a.msg)}`];
  if (a.action) lines.push(`   ${paint(S.dim, '→')} ${paint(S.text, a.action)}`);
  return lines;
}

// --- Modo simple: semaforo + accion ---
/**
 * Con un consejo pendiente (y avisos on) muestra solo el consejo; si no, una
 * linea con el estado del plan y cuanto gasta cada mensaje.
 * @param {object} d datos de collect()
 * @returns {string[]} lineas ya coloreadas
 */
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
/**
 * Una linea: modelo, peso de la charla, plan 5h/semana y modos 4D; el consejo
 * (si no es "Todo bien") va debajo.
 * @param {object} d datos de collect()
 * @returns {string[]} lineas ya coloreadas
 */
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
/**
 * Linea 1: modelo, contexto, costo, rama y modos 4D. Linea 2: plan (5h con
 * proyeccion del tope, 7d) y cache. Debajo, el consejo si hay. Las lineas
 * vacias se descartan.
 * @param {object} d datos de collect()
 * @returns {string[]} lineas ya coloreadas
 */
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

// CLI: node statusline.js mode <simple|normal|experto|silencio|avisos|tema>
// (lo usa la skill /barra). Sin argumento imprime el estado (con el tema
// efectivo, THEME, el mismo que pinta el render) y sale 0; con uno
// invalido, el uso y sale 1. Preserva las demas claves del archivo.
if (process.argv[2] === 'mode') {
  const m = process.argv[3];
  const st = STATE;
  const avisos = () => (st.quiet === false ? 'avisos' : 'silencio');
  if (m === 'silencio' || m === 'avisos') {
    st.quiet = m === 'silencio';
  } else if (MODES.includes(m)) {
    st.mode = m;
  } else if (isTheme(m)) {
    st.theme = m;
  } else {
    console.log(`Modo actual: ${readMode(st)} (${avisos()}, tema ${THEME}). Uso: node statusline.js mode ${MODES.join('|')}|silencio|avisos|<tema: ${Object.keys(THEMES).join(', ')}>`);
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
// Por que el timeout: si Claude Code (u otro runner) no cierra stdin, el proceso
// quedaria colgado y la barra en blanco; mejor una barra con datos parciales que
// ninguna. `done` evita pintar dos veces (timeout + end), y `unref` no deja que
// el timer mantenga vivo el proceso cuando stdin ya termino.
let input = '';
let done = false;
function render() {
  if (done) return;
  done = true;
  let s = {};
  try { s = (parseJson(input) || {}); } catch { /* sin datos o cortado */ }
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
