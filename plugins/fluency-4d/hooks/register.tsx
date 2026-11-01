import { atom, read, update } from 'claude-code'
import type { Color, EngineInterface, Register, RenderChildren } from 'claude-code'

import type { Panel4dLive, Panel4dPrefs, Panel4dTab, Panel4dUi } from '../types'

// Panel 4D (parte de fluency-4d): /panel abre un pane lateral (dock
// en fullscreen, inline arriba del prompt si no) con pestañas. El comando se
// registra como 'panel'; el namespace lo pone el plugin. Los ajustes se editan
// en un BORRADOR ($.state) y
// nada se escribe hasta Guardar: entonces van a ~/.claude/fluency4d/*.json (los
// mismos archivos que leen statusline.js y los hooks de fluency-4d), al /config
// de Claude (tema) y a los comandos integrados (/effort, /model, /fast,
// /autocompact). Las acciones de sesión (/compact, /clear, /handoff, atajos)
// corren al toque.
//
// Cómo se invoca: es un hooks module del engine de mods de Claude Code,
// declarado en hooks/hooks.json bajo "modules". El engine importa este archivo
// y llama a `register(on)` una vez por carga (y de nuevo en cada reload del
// mod, que pierde las variables del módulo). Todo pasa por los
// hooks que registra `on(...)`: session.start, command.run (/panel), ui.close,
// ui.focus, ui.render, turn.step y turn.complete.
//
// Lee: ~/.claude/fluency4d/{statusline,adhd,caveman,verify,panel4d}.json, los
// settings (effortLevel, modelSettings, autoCompactWindow, model), /config
// (theme), <config>/themes/*.json y el uso/modelo de la sesión.
// Escribe (solo al Guardar): esos mismos JSON de fluency4d (merge, preservando
// claves ajenas), el tema por /config y los comandos integrados. El estado del
// pane (borrador, foco, pestaña) vive en atoms ($.state), nunca en disco.

type $ = EngineInterface
type Json = Record<string, unknown>
type FlagName = 'adhd' | 'caveman' | 'verify'
type Tab = Panel4dTab
type Opt = readonly [value: string, shown: string]
type SettingId =
  | 'bar.mode'
  | 'bar.theme'
  | 'bar.quiet'
  | 'bar.cut'
  | 'claude.theme'
  | 'model.effort'
  | 'model.model'
  | 'model.fast'
  | 'mode.adhd'
  | 'mode.caveman'
  | 'mode.verify'
  | 'session.autocompact'
  | 'notify.on'
  | 'notify.ttl'
// `about`: una descripción corta por valor (la ayuda muestra solo la del valor
// elegido); `hint`, la de respaldo para valores sin descripción propia.
type Setting = {
  id: SettingId
  tab: Tab
  label: string
  hint: string
  options: readonly Opt[]
  about?: Readonly<Record<string, string>>
}
type ProfileName = 'foco' | 'pesado' | 'ahorro'

const PANE = 'panel-4d'
// Pedido de apertura del pane (se reusa al reabrir tras un Esc con cambios).
const OPEN = {
  id: PANE,
  title: 'Panel 4D',
  focus: true,
  // Sin fondo propio: una capa mas clara que el chat se roba la atencion (HIG dark mode).
  backgroundColor: 'transparent',
  closeOnEscape: true,
  columns: 64,
  rows: 26,
} as const

const BAR_MODES = ['simple', 'normal', 'experto'] as const
const THEMES = ['tokyo-night', 'catppuccin', 'nord', 'gruvbox', 'templado'] as const
const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max'] as const
const ADHD_LEVELS = ['auto', 'lite', 'full'] as const
const CAVEMAN_LEVELS = ['auto', 'lite', 'full', 'ultra'] as const
const AUTOCOMPACT: readonly Opt[] = [
  ['200000', '200k'],
  ['400000', '400k'],
  ['600000', '600k'],
  ['auto', 'Default'],
]
// Opción cuyo texto visible es el mismo valor.
const same = (v: string): Opt => [v, v]

/**
 * Tabla de ajustes del panel: una fila por entrada, en este orden, dentro de su
 * pestaña. Enter cicla `options`; `about` es la ayuda por valor. Las opciones de
 * 'claude.theme' son dinámicas (salen de /config y de los temas custom, ver
 * optionsOf); por eso acá van vacías.
 */
const SETTINGS: readonly Setting[] = [
  {
    id: 'bar.mode',
    tab: 'barra',
    label: 'Modo',
    hint: 'vista de la barra de estado',
    about: {
      simple: 'semáforo y una sola acción',
      normal: 'barras de contexto y plan',
      experto: 'todo el detalle: costo y caché',
    },
    options: BAR_MODES.map(same),
  },
  {
    id: 'bar.theme',
    tab: 'barra',
    label: 'Tema de la barra',
    hint: 'colores de la barra y de este panel',
    about: {
      'tokyo-night': 'azules y violetas',
      catppuccin: 'pasteles suaves',
      nord: 'azules fríos y grises',
      gruvbox: 'tonos tierra cálidos',
      templado: 'grises cálidos y acento naranja',
    },
    options: THEMES.map(same),
  },
  {
    id: 'bar.quiet',
    tab: 'barra',
    label: 'Avisos',
    hint: 'avisos de la barra',
    about: {
      avisos: 'consejos y etiquetas en la barra',
      silencio: 'la barra muestra solo números',
    },
    options: [
      ['avisos', 'avisos'],
      ['silencio', 'silencio'],
    ],
  },
  {
    id: 'bar.cut',
    tab: 'barra',
    label: 'Charla larga',
    hint: 'desde dónde avisa "charla larga"',
    about: {
      '0.25': 'avisa charla larga a 1/4 de ventana',
      '0.5': 'avisa charla larga a media ventana',
      '0.75': 'avisa charla larga a 3/4 de ventana',
    },
    options: [
      ['0.25', '25%'],
      ['0.5', '50%'],
      ['0.75', '75%'],
    ],
  },
  {
    id: 'claude.theme',
    tab: 'barra',
    label: 'Tema de Claude',
    hint: 'tema de todo Claude Code (/config)',
    options: [],
  },
  {
    id: 'model.effort',
    tab: 'modelo',
    label: 'Esfuerzo',
    hint: 'cuánto razona por respuesta',
    about: {
      low: 'razona poco, responde rápido',
      medium: 'equilibrio de razonamiento',
      high: 'razona más en cada respuesta',
      xhigh: 'razona mucho más, va más lento',
      max: 'el máximo razonamiento posible',
    },
    options: EFFORTS.map(same),
  },
  {
    id: 'model.model',
    tab: 'modelo',
    label: 'Modelo',
    hint: 'modelo de la sesión',
    about: {
      opus: 'el más capaz para trabajo complejo',
      sonnet: 'equilibrio de capacidad y costo',
      haiku: 'el más rápido y barato',
    },
    options: ['opus', 'sonnet', 'haiku'].map(same),
  },
  {
    id: 'model.fast',
    tab: 'modelo',
    label: 'Fast mode',
    hint: 'velocidad de salida',
    about: {
      off: 'salida a velocidad normal',
      on: 'salida más rápida, si el modelo puede',
    },
    options: ['off', 'on'].map(same),
  },
  {
    id: 'mode.adhd',
    tab: 'modos',
    label: 'ADHD',
    hint: 'respuestas accionables',
    about: {
      off: 'respuestas en estilo normal',
      auto: 'pasos accionables cuando conviene',
      lite: 'estructura liviana y próximo paso',
      full: 'todo en pasos numerados y concretos',
    },
    options: ['off', ...ADHD_LEVELS].map(same),
  },
  {
    id: 'mode.caveman',
    tab: 'modos',
    label: 'Caveman',
    hint: 'respuestas cortas',
    about: {
      off: 'respuestas con largo normal',
      auto: 'recorta relleno cuando conviene',
      lite: 'recorte suave del relleno',
      full: 'respuestas cortas, ahorra tokens',
      ultra: 'lo mínimo indispensable',
    },
    options: ['off', ...CAVEMAN_LEVELS].map(same),
  },
  {
    id: 'mode.verify',
    tab: 'modos',
    label: 'Verify-diff',
    hint: 'verificar el diff al cerrar',
    about: {
      off: 'sin recordatorio al cerrar tareas',
      on: 'recuerda verificar el diff al cerrar',
    },
    options: ['off', 'on'].map(same),
  },
  {
    id: 'session.autocompact',
    tab: 'sesion',
    label: 'Auto-compact',
    hint: 'desde cuántos tokens se auto-compacta',
    about: {
      '200000': 'compacta antes, contexto más corto',
      '400000': 'compacta a mitad de camino',
      '600000': 'compacta tarde, más contexto',
      auto: 'el umbral que elige Claude Code',
    },
    options: AUTOCOMPACT,
  },
  {
    id: 'notify.on',
    tab: 'sesion',
    label: 'Avisos de caché y plan',
    hint: 'toasts de caché y plan',
    about: {
      on: 'toasts de caché por vencer y plan 5h',
      off: 'sin toasts de caché ni de plan',
    },
    options: ['on', 'off'].map(same),
  },
  {
    id: 'notify.ttl',
    tab: 'sesion',
    label: 'TTL de la caché',
    hint: 'cuándo avisa que vence la caché',
    about: {
      '5': 'avisa en el último minuto',
      '60': 'avisa 5 min antes de que venza',
    },
    options: [
      ['5', '5 min'],
      ['60', '1 h'],
    ],
  },
]
const SETTING = new Map<string, Setting>(SETTINGS.map(s => [s.id, s]))
// Si el elemento `key` vive en la pestaña `tab` (los del pie y las pestañas, en todas).
const isInTab = (key: string, tab: Tab): boolean => {
  const s = SETTING.get(key)
  if (s) return s.tab === tab
  if (key.startsWith('profile-')) return tab === 'perfiles'
  if (key in ACTIONS || key.startsWith('clear-')) return tab === 'sesion'
  return true
}
// El primer elemento enfocable de cada pestaña (adonde va el foco al cambiar).
const firstFocus = (tab: Tab): string =>
  tab === 'perfiles' ? 'profile-foco' : (SETTINGS.find(s => s.tab === tab)?.id ?? `tab-${tab}`)
// Rótulo corto en la fila (la sección ya dice de qué es); el largo va en los toasts.
const ROW_LABEL: Partial<Record<SettingId, string>> = { 'bar.theme': 'Tema' }

// Pestañas: [id, rótulo, rótulo corto para panes angostos (W < 47)].
const TABS: readonly (readonly [Tab, string, string])[] = [
  ['barra', 'Barra', 'Barra'],
  ['modelo', 'Modelo', 'Modelo'],
  ['modos', 'Modos 4D', '4D'],
  ['sesion', 'Sesión', 'Sesión'],
  ['perfiles', 'Perfiles', 'Perfiles'],
]
// Ayuda de respaldo de cada pestaña (cuando el foco no está en nada con ayuda propia).
const TAB_HINT: Record<Tab, string> = {
  barra: 'Nada se aplica hasta Guardar',
  modelo: 'Al Guardar corren /effort, /model y /fast',
  modos: 'ADHD y Caveman se excluyen entre sí',
  sesion: 'Acciones corren ya; ajustes, al Guardar',
  perfiles: 'Carga el borrador; Guardar lo aplica',
}
// Ayuda de los botones del pie y de las confirmaciones (para el elemento con foco).
const FOCUS_HINT: Record<string, string> = {
  exit: 'Cierra; si hay cambios, pregunta una vez',
  'save-exit': 'Aplica el borrador y cierra el panel',
  save: 'Aplica el borrador y deja el panel abierto',
  back: 'Vuelve al panel sin descartar el borrador',
  discard: 'Cierra el panel sin aplicar el borrador',
  'clear-yes': 'Corre /clear ya y vacía el contexto',
  'clear-no': 'No corre /clear',
}
// Sangría de filas y botones dentro de cada sección.
const INDENT = 2
// Columna vertical de pestañas: ancho ("▌ Modos 4D" + aire) y el ancho mínimo
// de cuerpo del pane para usarla (debajo, pestañas en fila): con 58 el
// contenido mide 43, lo justo para que las ayudas entren en una línea.
const TAB_COL = 11
const VERTICAL_MIN = 58

// Perfiles: atajos que cargan varios valores en el borrador (los valores, en
// loadProfile). `desc` se parte por " · " para el wrap de la descripción.
const PROFILES: Record<ProfileName, { label: string; desc: string }> = {
  foco: { label: 'Foco', desc: 'barra simple en silencio · ADHD · esfuerzo medium' },
  pesado: { label: 'Trabajo pesado', desc: 'barra experto con avisos · esfuerzo high' },
  ahorro: { label: 'Ahorro', desc: 'esfuerzo low · fast off · auto-compact 400k' },
}

// Acciones inmediatas y atajos de la pestaña Sesión (no pasan por el borrador).
// `strict`: el comando es de otro plugin; si no está listado no se intenta
// (ver runCmd). Los integrados (/compact, /clear) se corren aunque no figuren.
const ACTIONS: Record<string, { label: string; command: string; strict: boolean; hint: string }> = {
  'act-compact': {
    label: 'Compactar',
    command: 'compact',
    strict: false,
    hint: 'Corre /compact: resume y libera contexto',
  },
  'act-clear': {
    label: 'Limpiar…',
    command: 'clear',
    strict: false,
    hint: 'Corre /clear; la sesión queda en /resume',
  },
  'act-handoff': {
    label: 'Handoff',
    command: 'handoff',
    strict: true,
    hint: 'Guarda estado para otra sesión (/handoff)',
  },
  'short-sentinel-audit': {
    label: 'Sentinel audit',
    command: 'sentinel-audit',
    strict: true,
    hint: 'Auditoría completa (/sentinel-audit)',
  },
  'short-4d-status': {
    label: '4D status',
    command: '4d-status',
    strict: true,
    hint: 'Estado de fluency-4d aquí (/4d-status)',
  },
}

// --- Paletas: el pane se pinta con el tema de la barra (statusline.js) ---

type Palette = {
  dim: Color
  label: Color
  text: Color
  accent: Color
  ok: Color
  warn: Color
  bad: Color
  // Pastilla (pestaña activa, Guardar con pendientes): fondo apagado + texto claro.
  // Sin ella se usa inverse.
  pill?: Color
  pillText?: Color
  // Fondo muy apagado de la fila con foco y de los chips de acción.
  focusBg?: Color
  // Separadores (decorativos, tenues); sin ella, dim.
  rule?: Color
}
type Hex = Record<'dim' | 'label' | 'text' | 'accent' | 'ok' | 'warn' | 'bad' | 'pill' | 'pillText' | 'focusBg', string>
const hexes = (h: Hex): Palette => ({
  dim: `#${h.dim}`,
  label: `#${h.label}`,
  text: `#${h.text}`,
  accent: `#${h.accent}`,
  ok: `#${h.ok}`,
  warn: `#${h.warn}`,
  bad: `#${h.bad}`,
  pill: `#${h.pill}`,
  pillText: `#${h.pillText}`,
  focusBg: `#${h.focusBg}`,
})
// dim..bad: los mismos hex que THEMES en statusline/statusline.js (de este
// plugin); pill y focusBg, tonos de fondo de cada paleta.
const BAR_PALETTES: Record<string, Palette> = {
  'tokyo-night': hexes({
    dim: '565f89',
    label: '9aa5ce',
    text: 'c0caf5',
    accent: 'bb9af7',
    ok: '9ece6a',
    warn: 'e0af68',
    bad: 'f7768e',
    pill: '3d59a1',
    pillText: 'c0caf5',
    focusBg: '292e42',
  }),
  catppuccin: hexes({
    dim: '6c7086',
    label: 'a6adc8',
    text: 'cdd6f4',
    accent: 'cba6f7',
    ok: 'a6e3a1',
    warn: 'f9e2af',
    bad: 'f38ba8',
    pill: '585b70',
    pillText: 'cdd6f4',
    focusBg: '313244',
  }),
  nord: hexes({
    dim: '4c566a',
    label: 'd8dee9',
    text: 'eceff4',
    accent: 'b48ead',
    ok: 'a3be8c',
    warn: 'ebcb8b',
    bad: 'bf616a',
    pill: '4c566a',
    pillText: 'eceff4',
    focusBg: '3b4252',
  }),
  gruvbox: hexes({
    dim: '928374',
    label: 'bdae93',
    text: 'ebdbb2',
    accent: 'd3869b',
    ok: 'b8bb26',
    warn: 'fabd2f',
    bad: 'fb4934',
    pill: '665c54',
    pillText: 'ebdbb2',
    focusBg: '3c3836',
  }),
  // "Acento puntual": crema + grises cálidos y un único acento, el naranja de
  // Claude. Los colores salen del tema de Claude (custom:templado,
  // themes/templado.json de este plugin): el naranja es la clave `claude`, no
  // un hex. Solo los fondos van en hex.
  templado: {
    dim: 'subtle',
    label: 'inactive',
    text: 'text',
    accent: 'claude',
    ok: 'success',
    warn: 'warning',
    bad: 'error',
    pill: '#2e2a26',
    pillText: 'text',
    focusBg: '#201d1a',
    rule: 'promptBorder',
  },
}
// Sin tema de barra (o uno desconocido): las claves del tema de Claude.
const ENGINE_PALETTE: Palette = {
  dim: 'inactive',
  label: 'subtle',
  text: 'text',
  accent: 'claude',
  rule: 'promptBorder',
  ok: 'success',
  warn: 'warning',
  bad: 'error',
}
const paletteOf = (theme: string | undefined): Palette =>
  (theme !== undefined && BAR_PALETTES[theme]) || ENGINE_PALETTE

// Rótulo de sección de cada ajuste (las filas se agrupan bajo él).
const SECTION_OF: Record<SettingId, string> = {
  'bar.mode': 'BARRA DE ESTADO',
  'bar.theme': 'BARRA DE ESTADO',
  'bar.quiet': 'BARRA DE ESTADO',
  'bar.cut': 'BARRA DE ESTADO',
  'claude.theme': 'CLAUDE',
  'model.effort': 'MODELO',
  'model.model': 'MODELO',
  'model.fast': 'MODELO',
  'mode.adhd': 'ESTILO DE RESPUESTA',
  'mode.caveman': 'ESTILO DE RESPUESTA',
  'mode.verify': 'DILIGENCIA',
  'session.autocompact': 'CONTEXTO',
  'notify.on': 'AVISOS',
  'notify.ttl': 'AVISOS',
}

// La primera variante que entra en `width` (la última si ninguna entra).
const fit = (width: number, ...variants: string[]): string =>
  variants.find(v => v.length <= width) ?? variants[variants.length - 1] ?? ''

// Parte `text` en líneas de hasta `width` por palabra, sin truncar (una palabra
// más larga que el ancho se corta en trozos).
const wrapWords = (text: string, width: number): string[] => {
  const w = Math.max(1, width)
  const lines: string[] = []
  let cur = ''
  for (const word of text.split(/\s+/).filter(Boolean)) {
    let rest = word
    while (rest.length > w) {
      if (cur) lines.push(cur), (cur = '')
      lines.push(rest.slice(0, w))
      rest = rest.slice(w)
    }
    if (!rest) continue
    if (!cur) cur = rest
    else if (cur.length + 1 + rest.length <= w) cur += ` ${rest}`
    else lines.push(cur), (cur = rest)
  }
  if (cur) lines.push(cur)
  return lines.length > 0 ? lines : ['']
}

// Agrupa elementos de ancho dado en filas de hasta `width` con `gap` entre
// ellos (un elemento solo, aunque no entre, va en su propia fila).
const pack = <T,>(items: readonly T[], widthOf: (x: T) => number, width: number, gap: number): T[][] => {
  const rows: T[][] = []
  let cur: T[] = []
  let used = 0
  for (const it of items) {
    const w = widthOf(it)
    if (cur.length > 0 && used + gap + w > width) rows.push(cur), (cur = []), (used = 0)
    used += (cur.length > 0 ? gap : 0) + w
    cur.push(it)
  }
  if (cur.length > 0) rows.push(cur)
  return rows
}

// Segmentos unidos por " · ", partidos en líneas que entren en `width`; un
// segmento que solo no entra se parte por palabra.
const packSegments = (segs: readonly string[], width: number): string[] =>
  pack(
    segs.flatMap(s => (s.length > width ? wrapWords(s, width) : [s])),
    s => s.length,
    width,
    3,
  ).map(r => r.join(' · '))

// --- Estado ---

const DEFAULT_PREFS: Panel4dPrefs = { notify: true, cacheTtlMin: 5 }
const DEFAULT_UI: Panel4dUi = { tab: 'barra', draft: {}, current: {}, themeOptions: [] }

// Atoms del engine ($.state; contrato en types/index.d.ts), con su default y
// una etiqueta de forma (`shape`). Tras un reload pueden volver al default (ver
// el reloj de session.start), así que lo que importa se relee del disco.
// - live: datos de la sesión (uso, modelo, esfuerzo, último turno).
// - prefs: preferencias del panel (copia de panel4d.json).
// - ui: el pane (pestaña, borrador, valores reales, foco, confirmaciones).
const live = atom({ plugin: 'fluency-4d', key: 'live' } as const, {}, { shape: 'live-1' })
const prefs = atom({ plugin: 'fluency-4d', key: 'prefs' } as const, DEFAULT_PREFS, {
  shape: 'prefs-1',
})
const ui = atom({ plugin: 'fluency-4d', key: 'ui' } as const, DEFAULT_UI, { shape: 'ui-1' })

const errText = (err: unknown) => (err instanceof Error ? err.message : String(err))
const isObj = (v: unknown): v is Json => v !== null && typeof v === 'object' && !Array.isArray(v)
const norm = (s: string) =>
  s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .trim()

// --- Archivos de estado: escrituras serializadas y verificadas ---

// Una cola por archivo: cada read-modify-write espera al anterior, así dos
// cambios seguidos o en paralelo nunca leen la misma versión y se pisan.
const queues = new Map<string, Promise<unknown>>()
function serialized<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const run = (queues.get(key) ?? Promise.resolve()).then(fn, fn)
  queues.set(
    key,
    run.catch(() => undefined),
  )
  return run
}

// El home como os.homedir() / Path.home(): en Windows USERPROFILE y después HOME;
// en el resto HOME (USERPROFILE solo de respaldo). El módulo no ve la plataforma:
// la deduce de OS=Windows_NT, que Windows define siempre y POSIX no.
/**
 * Home del usuario, resuelto igual que statusline.js (os.homedir) y los hooks
 * Python (Path.home), para que los tres lean y escriban los mismos archivos.
 * @throws si no hay ni USERPROFILE ni HOME
 */
async function homeDir($: $): Promise<string> {
  const isWin = (await $.env.get('OS')) === 'Windows_NT'
  const profile = await $.env.get('USERPROFILE')
  const posixHome = await $.env.get('HOME')
  const home = isWin ? profile || posixHome : posixHome || profile
  if (!home) throw new Error('no encuentro USERPROFILE ni HOME')
  return home
}

// ~/.claude/fluency4d/<name>.json con barras `/` (sirven en Windows y POSIX).
async function flagPath($: $, name: string): Promise<string> {
  const home = await homeDir($)
  return `${home.replace(/\\/g, '/').replace(/\/$/, '')}/.claude/fluency4d/${name}.json`
}

// La carpeta de config de Claude: CLAUDE_CONFIG_DIR, si no ~/.claude (como el engine).
async function claudeDir($: $): Promise<string> {
  const dir = await $.env.get('CLAUDE_CONFIG_DIR')
  const clean = (p: string) => p.replace(/\\/g, '/').replace(/\/$/, '')
  if (dir) return clean(dir)
  const home = await homeDir($)
  return `${clean(home)}/.claude`
}

// Temas custom de Claude Code: <config>/themes/<slug>.json (hasta 256KB), que el
// engine selecciona como "custom:<slug>". Ilegibles o sin objeto: se saltean.
async function customThemes($: $): Promise<{ value: string; name: string }[]> {
  try {
    const dir = `${await claudeDir($)}/themes`
    if (!(await $.fs.exists(dir))) return []
    const out: { value: string; name: string }[] = []
    for (const f of await $.fs.list(dir)) {
      if (f.kind !== 'file' || !f.name.endsWith('.json') || f.size > 262_144) continue
      const slug = f.name.slice(0, -'.json'.length)
      let name = slug
      try {
        const parsed: unknown = parseJson(String(await $.fs.read(`${dir}/${f.name}`)))
        if (!isObj(parsed)) continue
        if (typeof parsed.name === 'string' && parsed.name.trim() !== '') name = parsed.name
      } catch {
        continue
      }
      out.push({ value: `custom:${slug}`, name })
    }
    return out.sort((a, b) => a.name.localeCompare(b.name))
  } catch {
    return []
  }
}

// JSON.parse sin el BOM UTF-8 inicial (Notepad, PowerShell 5 `-Encoding utf8`),
// igual que parseJson de statusline.js: con BOM, JSON.parse tira y el archivo
// se ignoraba. Lo usan todas las lecturas de JSON del panel (statusline,
// panel4d, flags y temas custom).
function parseJson(text: string): unknown {
  return JSON.parse(text.charCodeAt(0) === 0xfeff ? text.slice(1) : text)
}

// Estricta: un archivo que no existe es {}; uno ilegible o con JSON roto TIRA,
// para no pisarlo con un objeto vacío y perder sus otras claves. Con BOM se lee
// bien, y al reescribirlo (mergeJson) queda sin BOM.
async function readStrict($: $, path: string): Promise<Json> {
  if (!(await $.fs.exists(path))) return {}
  const text = String(await $.fs.read(path))
  if (text.trim() === '') return {}
  let parsed: unknown
  try {
    parsed = parseJson(text)
  } catch {
    throw new Error(`${path} tiene JSON inválido; no lo piso`)
  }
  if (!isObj(parsed)) throw new Error(`${path} no es un objeto JSON; no lo piso`)
  return parsed
}

// Para mostrar: cualquier problema = sin datos (nunca se usa para escribir).
async function readSoft($: $, name: string): Promise<Json> {
  try {
    return await readStrict($, await flagPath($, name))
  } catch {
    return {}
  }
}

// Lee, mezcla, escribe y relee: devuelve lo que QUEDÓ en el archivo y tira si
// alguna clave del parche no quedó guardada.
async function mergeJson($: $, name: string, patch: Json): Promise<Json> {
  const path = await flagPath($, name)
  return serialized(path, async () => {
    const merged = { ...(await readStrict($, path)), ...patch }
    await $.fs.write(path, `${JSON.stringify(merged)}\n`)
    const back = await readStrict($, path)
    for (const [k, v] of Object.entries(patch)) {
      if (JSON.stringify(back[k]) !== JSON.stringify(v)) {
        throw new Error(`${name}.json no quedó con ${k}=${JSON.stringify(v)}`)
      }
    }
    return back
  })
}

// ADHD y Caveman son excluyentes (así los escriben los skills de fluency-4d).
async function setMode($: $, name: FlagName, patch: Json): Promise<void> {
  await mergeJson($, name, patch)
  if (patch.on === true && name !== 'verify') {
    const other = name === 'adhd' ? 'caveman' : 'adhd'
    const st = await readSoft($, other)
    if (st.on === true) await mergeJson($, other, { on: false })
  }
}

/**
 * Carga panel4d.json en el atom `prefs` y devuelve lo cargado. Lectura blanda:
 * sin archivo o roto quedan los defaults (avisos on, TTL 5 min); cualquier TTL
 * que no sea 60 cuenta como 5.
 */
async function loadPrefs($: $): Promise<Panel4dPrefs> {
  const p = await readSoft($, 'panel4d')
  return update($, prefs, () => ({
    notify: p.notify !== false,
    cacheTtlMin: p.cacheTtlMin === 60 ? 60 : 5,
  }))
}

// --- Lecturas para mostrar ---

// Mismos defaults que statusline.js: experto, templado y silencio (salvo quiet:false).
// Tienen que coincidir: el panel muestra como "actual" lo que la barra aplica
// de verdad; si no, un archivo sin `mode` se vería distinto en cada lado.
const barMode = (st: Json) => (BAR_MODES.some(m => m === st.mode) ? String(st.mode) : 'experto')
const barTheme = (st: Json) => (THEMES.some(t => t === st.theme) ? String(st.theme) : 'templado')

/**
 * Valor de un modo 4D (ADHD/Caveman) para el panel, a partir de su flag.
 * @param st contenido del flag (adhd.json / caveman.json)
 * @param levels niveles válidos de ese modo
 * @returns el nivel si on === true y el nivel es válido; si no, 'off'
 */
function modeValue(st: Json, levels: readonly string[]): string {
  // Igual que la barra y hook_utils: sin un nivel válido el modo cuenta como apagado.
  if (st.on !== true) return 'off'
  return typeof st.level === 'string' && levels.includes(st.level) ? st.level : 'off'
}

function modelAlias(model: string | undefined): string | undefined {
  const m = (model ?? '').toLowerCase()
  return ['opus', 'sonnet', 'haiku'].find(a => m.includes(a))
}

// Mismo formato y redondeo que fmtTokens de statusline/statusline.js, para que
// el panel y la barra muestren igual el mismo número: M exacto sin decimales
// ("1M"), M no exacto con 2 y k con 1; < 1000 redondeado a entero. Lo que en k
// daría "1000.0k" (999_950..999_999) sube a "1.00M". Fuera de dominio (NaN,
// Infinity, negativo, no number, o un texto de más de 8 caracteres o con
// notación científica, p. ej. >= 1e10) = "—". El cuerpo es JS puro y da
// exactamente lo mismo que el de la barra: lo verifica
// statusline/test/fmt_tokens_parity.test.js.
function fmtTokens(n: number): string {
  if (typeof n !== 'number' || !Number.isFinite(n) || n < 0) return '—'
  const k = (n / 1e3).toFixed(1)
  let s
  if (n < 999.5) s = String(Math.round(n))
  else if (n < 1e6 && k !== '1000.0') s = `${k}k`
  else s = `${(n / 1e6).toFixed(n % 1e6 === 0 ? 0 : 2)}M`
  return s.length <= 8 && /^\d+(\.\d+)?[kM]?$/.test(s) ? s : '—'
}

/**
 * Número finito desde un valor de un JSON de estado: solo `number` o string
 * numérico no vacío. Nunca `Number()` sobre un objeto: llama a su
 * toString/valueOf y con `{"toString":[]}` tira TypeError (igual que num() de
 * statusline.js).
 * @returns el número, o undefined si no es un finito
 */
function finiteNum(v: unknown): number | undefined {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN
  return Number.isFinite(n) ? n : undefined
}

function hhmm(iso: string | undefined): string | undefined {
  if (!iso) return undefined
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return undefined
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}hs`
}

/**
 * Minutos que le quedan a la caché, estimados desde el fin del último turno y
 * el TTL (el engine no expone el vencimiento real). Negativo = ya venció.
 * @param lastTurnAt epoch ms del último turno del hilo principal
 * @param ttlMin TTL configurado en el panel (5 o 60)
 * @param now epoch ms actual
 * @returns undefined si todavía no hubo turno
 */
function cacheMinsLeft(lastTurnAt: number | undefined, ttlMin: number, now: number) {
  if (lastTurnAt === undefined) return undefined
  return Math.floor((lastTurnAt + ttlMin * 60_000 - now) / 60_000)
}

// --- Datos de la sesión ---

async function refreshUsage($: $): Promise<Panel4dLive> {
  const patch: Panel4dLive = {}
  try {
    const u = await $.session.usage()
    const five = u.rateLimits.find(r => r.kind === 'five_hour')
    patch.tokens = u.context.tokens
    patch.window = u.context.window
    patch.percent = u.context.percent
    patch.fiveHour = five?.percentUsed
    patch.fiveHourResetsAt = five?.resetsAt
  } catch {
    // sin datos de uso: el resumen lo omite
  }
  try {
    patch.model = await $.session.model()
  } catch {
    // sin modelo: queda el último visto
  }
  return update($, live, l => ({ ...l, ...patch }))
}

// Esfuerzo y auto-compact guardados en settings, para mostrar algo antes del primer turno.
async function readSettingsHints($: $): Promise<void> {
  try {
    const global = await $.settings.read({ key: 'effortLevel' })
    const window = await $.settings.read({ key: 'autoCompactWindow' })
    // modelSettings.<modelo>.effortLevel pisa al global (p. ej. Opus 5.5 en medium con global high).
    const perModel = await $.settings.read({ key: 'modelSettings' })
    const model = (await read($, live)).model ?? (await $.settings.read({ key: 'model' }))
    let effort = typeof global === 'string' ? global : undefined
    if (isObj(perModel) && typeof model === 'string' && model) {
      const id = model.toLowerCase()
      const key = Object.keys(perModel).find(k => {
        const kk = k.toLowerCase()
        return kk === id || id.includes(kk) || kk.includes(id)
      })
      const entry = key === undefined ? undefined : perModel[key]
      if (isObj(entry) && typeof entry.effortLevel === 'string') effort = entry.effortLevel
    }
    await update($, live, l => ({
      ...l,
      effort: l.effort ?? effort,
      autoCompact:
        l.autoCompact ??
        (typeof window === 'number' || typeof window === 'string' ? String(window) : undefined),
    }))
  } catch {
    // settings ilegibles: no se muestra el valor actual
  }
}

/**
 * Los valores REALES de cada ajuste (lo que hay hoy en archivos, settings y
 * sesión), contra los que se compara el borrador. Solo lee; lecturas blandas
 * (un archivo roto = default). Ajustes sin dato (p. ej. esfuerzo antes del
 * primer turno) quedan fuera de `current` y se muestran como "—".
 * @returns current, el tema de la barra para pintar el pane y las opciones y
 *   nombres del tema de Claude (de /config + temas custom)
 */
async function loadSnapshot(
  $: $,
): Promise<Pick<Panel4dUi, 'current' | 'paneTheme' | 'themeOptions' | 'themeNames'>> {
  const [st, adhd, caveman, verify] = await Promise.all([
    readSoft($, 'statusline'),
    readSoft($, 'adhd'),
    readSoft($, 'caveman'),
    readSoft($, 'verify'),
  ])
  const l = await read($, live)
  const p = await read($, prefs)
  const cavemanValue = modeValue(caveman, CAVEMAN_LEVELS)
  const cur: Record<string, string> = {
    'bar.mode': barMode(st),
    'bar.theme': barTheme(st),
    'bar.quiet': st.quiet === false ? 'avisos' : 'silencio',
    // ADHD cede ante caveman (adhd_injector.py): con caveman activo, ADHD no corre.
    // Se muestra 'off' porque es lo que el usuario recibe de verdad, igual que
    // la barra (statusline.js fluencyModes); si los dos flags quedaron on (p. ej.
    // editados a mano), gana caveman.
    'mode.adhd': cavemanValue === 'off' ? modeValue(adhd, ADHD_LEVELS) : 'off',
    'mode.caveman': cavemanValue,
    'mode.verify': verify.on === true ? 'on' : 'off',
    'notify.on': p.notify ? 'on' : 'off',
    'notify.ttl': String(p.cacheTtlMin),
  }
  // ADHD prendido pero oculto por caveman: su nivel real, para mostrarlo si
  // el borrador apaga caveman (ver baseOf).
  const adhdReal = modeValue(adhd, ADHD_LEVELS)
  if (cavemanValue !== 'off' && adhdReal !== 'off') cur[ADHD_HIDDEN] = adhdReal
  const f = finiteNum(st.cutFraction)
  cur['bar.cut'] = f !== undefined && f > 0 && f < 1 ? String(f) : '0.5'
  if (l.effort !== undefined) cur['model.effort'] = l.effort
  const alias = modelAlias(l.model)
  if (alias !== undefined) cur['model.model'] = alias
  if (l.fast !== undefined) cur['model.fast'] = l.fast
  if (l.autoCompact !== undefined) cur['session.autocompact'] = l.autoCompact
  let themeOptions: string[] = []
  try {
    const row = (await $.config.list()).find(r => r.key === 'theme')
    if (row) {
      if (Array.isArray(row.options)) themeOptions = row.options.filter(o => typeof o === 'string')
      if (typeof row.value === 'string') cur['claude.theme'] = row.value
    }
  } catch {
    // sin /config: la fila del tema de Claude queda sin opciones
  }
  const paneTheme =
    typeof st.theme === 'string' && Object.hasOwn(BAR_PALETTES, st.theme) ? st.theme : undefined
  // Los temas custom (~/.claude/themes/<slug>.json) no están en las opciones
  // de /config: se suman como custom:<slug>, con su `name` de etiqueta.
  const themeNames: Record<string, string> = {}
  for (const t of await customThemes($)) {
    if (!themeOptions.includes(t.value)) themeOptions.push(t.value)
    themeNames[t.value] = t.name
  }
  const curTheme = cur['claude.theme']
  if (curTheme !== undefined && !themeOptions.includes(curTheme)) themeOptions.push(curTheme)
  return { current: cur, paneTheme, themeOptions, themeNames }
}

// --- Borrador ---

// Clave de `current` (no es un ajuste) con el nivel real de un ADHD oculto por caveman.
const ADHD_HIDDEN = 'mode.adhd.hidden'

// Valor real contra el que se compara el borrador. ADHD oculto por caveman
// cuenta como off, salvo que el borrador apague caveman: entonces vale su nivel
// real, porque al guardar ADHD vuelve a correr. Así el panel lo muestra antes
// de guardar, y elegir ADHD off queda pendiente (y se escribe).
function baseOf(u: Panel4dUi, draft: Record<string, string>, id: string): string | undefined {
  const hidden = u.current[ADHD_HIDDEN]
  if (id === 'mode.adhd' && hidden !== undefined) {
    const caveman = draft['mode.caveman'] ?? u.current['mode.caveman']
    if (caveman === 'off') return hidden
  }
  return u.current[id]
}
const valueOf = (u: Panel4dUi, id: string): string | undefined =>
  u.draft[id] ?? baseOf(u, u.draft, id)
const pendingIds = (u: Panel4dUi): string[] =>
  Object.keys(u.draft).filter(k => u.draft[k] !== baseOf(u, u.draft, k))

function optionsOf(s: Setting, u: Panel4dUi): readonly Opt[] {
  return s.id === 'claude.theme'
    ? u.themeOptions.map((v): Opt => [v, u.themeNames?.[v] ?? v])
    : s.options
}

function shownOf(s: Setting, value: string | undefined, u: Panel4dUi): string {
  if (value === undefined) return '—'
  const hit = optionsOf(s, u).find(([v]) => v === value)
  if (hit) return hit[1]
  if (s.id === 'bar.cut') return `${Math.round(Number(value) * 100)}%`
  // Finito y > 0: "Infinity" o "1e400" (settings editado a mano) se muestran tal cual, no "InfinityM".
  const n = finiteNum(value)
  if (s.id === 'session.autocompact' && n !== undefined && n > 0) return fmtTokens(n)
  return value
}

// Pone `value` en el borrador; si es igual al real, saca la entrada (no queda pendiente).
function withValue(u: Panel4dUi, draft: Record<string, string>, id: string, value: string) {
  const next = { ...draft }
  if (value === baseOf(u, draft, id)) delete next[id]
  else next[id] = value
  return next
}

// ADHD y Caveman excluyentes también en el borrador.
function exclusive(u: Panel4dUi, draft: Record<string, string>, id: string, value: string) {
  if ((id !== 'mode.adhd' && id !== 'mode.caveman') || value === 'off') return draft
  const other = id === 'mode.adhd' ? 'mode.caveman' : 'mode.adhd'
  return valueOf({ ...u, draft }, other) === 'off' ? draft : withValue(u, draft, other, 'off')
}

async function cycle($: $, id: string): Promise<void> {
  const s = SETTING.get(id)
  if (!s) return
  await update($, ui, (u): Panel4dUi => {
    const opts = optionsOf(s, u)
    if (u.busy || opts.length === 0) return u
    const i = opts.findIndex(([v]) => v === valueOf(u, id))
    const value = opts[(i + 1) % opts.length]?.[0]
    if (value === undefined) return u
    const draft = exclusive(u, withValue(u, u.draft, id, value), id, value)
    return { ...u, draft, note: undefined, confirm: u.confirm === 'clear' ? 'clear' : undefined }
  })
}

async function loadProfile($: $, name: ProfileName): Promise<void> {
  const adhdLevel = (await readSoft($, 'adhd')).level
  const values: Record<string, string> =
    name === 'foco'
      ? {
          'bar.mode': 'simple',
          'bar.quiet': 'silencio',
          'mode.adhd': ADHD_LEVELS.some(l => l === adhdLevel) ? String(adhdLevel) : 'auto',
          'mode.caveman': 'off',
          'model.effort': 'medium',
        }
      : name === 'pesado'
        ? { 'bar.mode': 'experto', 'bar.quiet': 'avisos', 'model.effort': 'high' }
        : { 'model.effort': 'low', 'model.fast': 'off', 'session.autocompact': '400000' }
  await update($, ui, (u): Panel4dUi => {
    if (u.busy) return u
    let draft = u.draft
    for (const [id, v] of Object.entries(values)) draft = withValue(u, draft, id, v)
    const n = pendingIds({ ...u, draft }).length
    return {
      ...u,
      draft,
      confirm: undefined,
      note: `Perfil ${PROFILES[name].label} en el borrador (${n} pendiente${n === 1 ? '' : 's'}): Guardar lo aplica`,
    }
  })
}

// --- Comandos ---

// El nombre real del comando: exacto, o el de un plugin que termina en ":<name>".
async function findCommand($: $, name: string): Promise<string | undefined> {
  try {
    const list = await $.command.list()
    return (
      list.find(c => c.name === name)?.name ?? list.find(c => c.name.endsWith(`:${name}`))?.name
    )
  } catch {
    return undefined
  }
}

// Corre `/name args`; nunca tira: devuelve el motivo si falló. `strict`: si el
// comando no está listado ni lo intenta (atajos a plugins).
async function runCmd($: $, name: string, args = '', strict = false): Promise<string | undefined> {
  const found = await findCommand($, name)
  if (found === undefined && strict) return 'no está disponible en esta sesión'
  try {
    await $.command.run({ command: found ?? name, args })
    return undefined
  } catch (err) {
    return errText(err)
  }
}

// Acción inmediata de la pestaña Sesión, con toast del resultado.
async function runAction($: $, key: string): Promise<void> {
  const a = ACTIONS[key]
  if (!a) return
  const err = await runCmd($, a.command, '', a.strict)
  $.ui.toast(err === undefined ? `Panel 4D: listo, /${a.command}` : `Panel 4D: /${a.command} ${err}`)
}

// --- Guardar ---

// Aplica todo el borrador: archivos (en cola, releídos), /config y comandos.
// Devuelve false si ya había un guardado en curso o si algún paso falló; lo
// que falló (o no se llegó a aplicar) queda en el borrador.
// Cuenta los guardados, para que una foto leída antes de uno no lo pise.
let saveSeq = 0
/**
 * Guarda el borrador. `busy` se toma dentro de un único update (claimed), así
 * dos pulsaciones seguidas de Guardar nunca corren dos guardados. Cada grupo de
 * ajustes es un `step` independiente: uno que falla no frena a los demás. Al
 * final (siempre, en el finally) se relee la foto real y el borrador conserva
 * solo lo que no se aplicó.
 * @returns true si se aplicó todo (o no había nada); false si otro guardado
 *   estaba en curso o algún paso falló
 */
async function save($: $): Promise<boolean> {
  let claimed = false
  const u = await update($, ui, (x): Panel4dUi => {
    claimed = !x.busy
    return x.busy ? x : { ...x, busy: true, note: undefined }
  })
  if (!claimed) return false
  saveSeq++
  let ids: string[] = []
  const doneIds = new Set<string>()
  try {
    ids = pendingIds(u)
    if (ids.length === 0) {
      $.ui.toast('Panel 4D: no hay cambios para guardar')
      return true
    }
    const v = (id: SettingId) => (ids.includes(id) ? u.draft[id] : undefined)
    const shown = (id: SettingId) => {
      const s = SETTING.get(id)
      return s ? `${s.label} ${shownOf(s, u.draft[id], u)}` : id
    }
    const done: string[] = []
    const failed: string[] = []
    const step = async (sids: SettingId[], fn: () => Promise<unknown>) => {
      const label = sids.map(shown).join(', ')
      try {
        const err = await fn()
        if (typeof err === 'string') failed.push(`${label} (${err})`)
        else {
          done.push(label)
          for (const id of sids) doneIds.add(id)
        }
      } catch (err) {
        failed.push(`${label} (${errText(err)})`)
      }
    }

    // Barra: un solo parche a statusline.json (preserva las claves ajenas).
    const bar: Json = {}
    const barIds: SettingId[] = []
    const mode = v('bar.mode')
    if (mode !== undefined) (bar.mode = mode), barIds.push('bar.mode')
    const theme = v('bar.theme')
    if (theme !== undefined) (bar.theme = theme), barIds.push('bar.theme')
    const quiet = v('bar.quiet')
    if (quiet !== undefined) (bar.quiet = quiet === 'silencio'), barIds.push('bar.quiet')
    const cut = v('bar.cut')
    if (cut !== undefined) (bar.cutFraction = Number(cut)), barIds.push('bar.cut')
    if (barIds.length > 0) await step(barIds, () => mergeJson($, 'statusline', bar))

    // Modos 4D: primero los que se apagan, después los que se prenden.
    const modes = (['mode.adhd', 'mode.caveman'] as const)
      .filter(id => v(id) !== undefined)
      .sort((a, b) => Number(v(a) !== 'off') - Number(v(b) !== 'off'))
    for (const id of modes) {
      const value = v(id) ?? 'off'
      const name = id === 'mode.adhd' ? 'adhd' : 'caveman'
      await step([id], () =>
        setMode($, name, value === 'off' ? { on: false } : { on: true, level: value }),
      )
    }
    const verify = v('mode.verify')
    if (verify !== undefined) {
      await step(['mode.verify'], () => setMode($, 'verify', { on: verify === 'on' }))
    }

    // Preferencias del panel.
    const pp: Json = {}
    const ppIds: SettingId[] = []
    const notify = v('notify.on')
    if (notify !== undefined) (pp.notify = notify === 'on'), ppIds.push('notify.on')
    const ttl = v('notify.ttl')
    if (ttl !== undefined) (pp.cacheTtlMin = Number(ttl)), ppIds.push('notify.ttl')
    if (ppIds.length > 0) {
      await step(ppIds, async () => {
        await mergeJson($, 'panel4d', pp)
        await loadPrefs($)
      })
    }

    // Tema de todo Claude Code, por /config.
    const claudeTheme = v('claude.theme')
    if (claudeTheme !== undefined) {
      await step(['claude.theme'], async () => {
        const r = await $.config.set({ key: 'theme', value: claudeTheme })
        return r.deny
      })
    }

    // Comandos integrados.
    const cmds: [SettingId, string, keyof Panel4dLive][] = [
      ['model.effort', 'effort', 'effort'],
      ['model.model', 'model', 'model'],
      ['model.fast', 'fast', 'fast'],
      ['session.autocompact', 'autocompact', 'autoCompact'],
    ]
    for (const [id, command, field] of cmds) {
      const value = v(id)
      if (value === undefined) continue
      await step([id], async () => {
        const err = await runCmd($, command, value)
        if (err === undefined) await update($, live, l => ({ ...l, [field]: value }))
        return err
      })
    }

    const back = await readSoft($, 'statusline')
    const note =
      'cutFraction' in bar && back.quiet !== false
        ? ' (en silencio no se ve el aviso de charla larga)'
        : ''
    $.ui.toast(
      failed.length === 0
        ? `Panel 4D · guardado: ${done.join(' · ')}${note}`
        : `Panel 4D · guardado a medias. Falló: ${failed.join(', ')}.${done.length > 0 ? ` Quedó: ${done.join(' · ')}` : ''}${note}`,
    )
    return failed.length === 0
  } finally {
    const keep = new Set(ids.filter(id => !doneIds.has(id)))
    const snap = await loadSnapshot($).catch(() => undefined)
    await update($, ui, (x): Panel4dUi => {
      const draft = Object.fromEntries(Object.entries(x.draft).filter(([k]) => keep.has(k)))
      const empty = Object.keys(draft).length === 0
      return {
        ...x,
        ...snap,
        draft,
        busy: false,
        confirm: empty && x.confirm === 'exit' ? undefined : x.confirm,
      }
    })
  }
}

// Cierre ya confirmado: descarta el borrador y marca `closing` ANTES de cerrar,
// así el hook de ui.close nunca vuelve a preguntar.
async function closePane($: $): Promise<void> {
  await update($, ui, (x): Panel4dUi => ({
    ...x,
    draft: {},
    confirm: undefined,
    note: undefined,
    closing: true,
  }))
  try {
    await $.ui.close({ id: PANE })
  } finally {
    await update($, ui, (x): Panel4dUi => ({ ...x, closing: undefined }))
  }
}

// Botón Salir: con cambios pendientes abre la confirmación (una sola, en el
// pie); sin cambios cierra directo. Durante un guardado no hace nada.
async function exitPane($: $): Promise<void> {
  const u = await read($, ui)
  if (u.busy) return
  if (pendingIds(u).length > 0) {
    await update($, ui, (x): Panel4dUi => ({ ...x, confirm: 'exit' }))
    // El foco a "Volver": Enter por accidente no descarta nada (best-effort).
    void $.ui.focus({ requestId: PANE, key: 'back' }).catch(() => undefined)
    return
  }
  await closePane($)
}

// Pestaña pedida en `/panel <texto>`: alias, id exacto o prefijo (sin acentos ni
// mayúsculas). undefined si no hay texto o no coincide.
function tabOf(text: string): Tab | undefined {
  const t = norm(text)
  if (t === '') return undefined
  const alias: Record<string, Tab> = {
    '4d': 'modos',
    'modos 4d': 'modos',
    perfil: 'perfiles',
    avisos: 'sesion',
    notificaciones: 'sesion',
    atajos: 'sesion',
    apariencia: 'barra',
    tema: 'barra',
  }
  return alias[t] ?? TABS.map(([id]) => id).find(id => id === t || id.startsWith(t))
}

/**
 * Punto de entrada del hooks module: el engine lo llama con `on` para registrar
 * los hooks. Cada hook recibe `$` (la API del engine), el evento `e` y `next`
 * (el siguiente handler de la cadena: llamarlo deja seguir el comportamiento
 * por defecto; no llamarlo lo intercepta).
 */
export const register: Register = on => {
  // Marcas para no repetir el mismo aviso (se pierden con un reload, a propósito).
  let cacheToastFor: number | undefined
  let planToastFor: string | undefined

  // Al arrancar la sesión: registra /panel, carga las preferencias y arma el
  // reloj del aviso de caché. Nunca bloquea el arranque (siempre llama a next).
  on('session.start', async ($, e, next) => {
    try {
      await $.command.register({
        name: 'panel',
        description: 'Panel 4D: barra, modelo, modos 4D, sesión y perfiles (pane lateral)',
        argumentHint: `[${TABS.map(([id]) => id).join('|')}]`,
      })
    } catch (err) {
      $.ui.log(`fluency-4d: no pude registrar /panel: ${errText(err)}`, { to: 'debug' })
    }
    await loadPrefs($).catch(() => undefined)
    // Aviso de caché por vencer: con TTL de 1 h avisa a 5 min; con 5 min, al último minuto.
    $.clock.every(30_000, () => {
      void (async () => {
        // Releer el TTL del archivo: tras recargar el mod, `prefs` puede volver
        // al default (5 min) y session.start no se repite -> aviso falso.
        // También recoge un panel4d.json editado desde otra sesión. Es un
        // archivo chico, y cada 30 s el costo de leerlo es despreciable.
        await loadPrefs($).catch(() => undefined)
        const p = await read($, prefs)
        const { lastTurnAt } = await read($, live)
        if (!p.notify || lastTurnAt === undefined || cacheToastFor === lastTurnAt) return
        const left = cacheMinsLeft(lastTurnAt, p.cacheTtlMin, await $.clock.now())
        const threshold = p.cacheTtlMin >= 60 ? 5 : 1
        if (left !== undefined && left >= 0 && left < threshold) {
          cacheToastFor = lastTurnAt
          $.ui.toast(`La caché vence en ~${Math.max(left, 1)} min: si vas a seguir, escribí ahora`)
        }
      })().catch(() => undefined)
    })

    return next(e)
  })

  // /panel [pestaña]: abre (o enfoca) el pane. Si no estaba abierto, el
  // borrador arranca vacío = valores reales.
  on('command.run', { command: 'panel' }, async ($, e) => {
    const wanted = (e.args ?? '').trim()
    const tab = tabOf(wanted)
    if (wanted !== '' && !tab) {
      $.ui.toast(`Panel 4D: no hay una pestaña "${wanted}" (${TABS.map(([id]) => id).join(', ')})`)
    }
    const panes = await $.ui.panes().catch(() => [])
    const isOpen = panes.some(p => p.id === PANE)
    await loadPrefs($).catch(() => undefined)
    await refreshUsage($).catch(() => undefined)
    await readSettingsHints($)
    const snap = await loadSnapshot($)
    await update($, ui, (u): Panel4dUi =>
      isOpen
        ? { ...u, ...snap, tab: tab ?? u.tab }
        : { ...DEFAULT_UI, ...snap, tab: tab ?? u.tab ?? 'barra' },
    )
    const opened = await $.ui.open(OPEN)
    if (!opened.isPlaced) $.ui.toast(`Panel 4D: el panel no se pudo mostrar (${opened.reason})`)

    return {}
  })

  // Esc / la marca de cierre con cambios sin guardar: no cierra, pide confirmación.
  // Una sola confirmación: el segundo Esc la retira (Volver) en vez de cerrar o
  // preguntar de nuevo, así nunca hay un bucle de diálogos ni un descarte por
  // un Esc de más; descartar es siempre un botón explícito. Solo se interceptan
  // los cierres de una persona (origin 'person'); los demás, y el de closePane
  // (marcado con `closing`), pasan directo.
  on('ui.close', { id: PANE }, async ($, e, next) => {
    if (e.origin.kind === 'person') {
      const u = await read($, ui)
      // Mientras se guarda, Esc no cierra ni pregunta (como Salir).
      if (u.busy) return { value: undefined }
      // Esc con la confirmación ya abierta = Volver (nunca una segunda pregunta).
      if (u.confirm === 'exit') {
        await update($, ui, (x): Panel4dUi => ({ ...x, confirm: undefined }))
        return { value: undefined }
      }
      if (!u.closing && pendingIds(u).length > 0) {
        await update($, ui, (x): Panel4dUi => ({ ...x, confirm: 'exit' }))
        // Esc devolvió el teclado al prompt: se lo pedimos de vuelta (best-effort).
        void $.ui
          .open(OPEN)
          .then(() => $.ui.focus({ requestId: PANE, key: 'back' }))
          .catch(() => undefined)
        return { value: undefined }
      }
    }
    const closed = await next(e)
    await update($, ui, (x): Panel4dUi => ({
      ...x,
      draft: {},
      confirm: undefined,
      note: undefined,
      focus: undefined,
    }))
    return closed
  }).catch(($, e, next) => {
    // Por qué un .catch: este hook decide si el pane se cierra; si tirara, el
    // cierre dependería de cómo el engine trata el error. Acá siempre termina
    // en next(e), así un Esc nunca deja el panel trabado.
    // Falló leer o escribir el estado del pane. El cierre nunca queda colgado:
    // con next ya corrido el pane se cerró y next(e) repite ese resultado (solo
    // faltó limpiar el borrador, que el próximo /panel descarta).
    // Sin next no se pudo ver si había cambios sin guardar: se cierra igual y
    // se avisa, para que un borrador no se pierda en silencio.
    if (!next.called) {
      $.ui.toast(
        `Panel 4D: no se pudo revisar el borrador al cerrar (${errText(next.error)}); si había cambios sin guardar, se perdieron`,
      )
    }
    return next(e)
  })

  // Dónde está el foco, para la línea de ayuda contextual. Solo se anota si el
  // engine aceptó el cambio de foco; un error al anotar no frena el foco.
  on('ui.focus', { requestId: PANE }, async ($, e, next) => {
    const r = await next(e)
    if (r.deny === undefined) {
      await update($, ui, (u): Panel4dUi => ({ ...u, focus: e.element })).catch(() => undefined)
    }
    return r
  }).catch(($, e, next) => next(e))

  // Dibuja el pane entero en cada render: pestañas, secciones con sus filas,
  // ayuda, nota y pie, a partir de `ui`. No escribe estado; los efectos van en
  // los onPress (fire).
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const u = await read($, ui)
    const P = paletteOf(u.paneTheme)
    // Ancho útil: el del cuerpo del pane (tope 60) menos 1 columna de margen
    // izquierdo y 1 de margen derecho; nada se dibuja más ancho que W.
    const W = Math.max(16, Math.min(e.props.bodyColumns, 60) - 2)
    // Pestañas en columna a la izquierda desde VERTICAL_MIN columnas; más
    // angosto, en fila arriba. C = ancho del contenido (a la derecha de la
    // columna de pestañas y su separador, o W entero en el modo en fila).
    const wide = W >= VERTICAL_MIN - 2
    const C = wide ? W - TAB_COL - 2 : W
    const pend = pendingIds(u)
    const n = pend.length
    // Los handlers corren sueltos: un comando (/effort, /compact...) nunca
    // espera dentro de la pulsación.
    const fire = (fn: () => Promise<unknown>) => () => {
      void fn().catch(err => $.ui.toast(`Panel 4D: algo falló: ${errText(err)}`))
    }
    const rule = <Text color={P.rule ?? P.dim}>{'─'.repeat(W)}</Text>
    // Pastilla (pestaña activa): fondo apagado + texto en el acento; sin
    // paleta propia, inverse.
    const pill = (text: string) =>
      P.pill !== undefined ? (
        <Text backgroundColor={P.pill} color={P.accent} weight="bold">
          {` ${text} `}
        </Text>
      ) : (
        <Text inverse color={P.accent} weight="bold">
          {` ${text} `}
        </Text>
      )
    // Chip (acciones y botones del pie): texto con fondo. `primary` con el
    // fondo de acento apagado (más claro), `dim` apagado, `danger` en el rojo
    // apagado de la paleta. Sin paleta propia: corchetes.
    type Tone = 'normal' | 'primary' | 'dim' | 'danger'
    const toneColor = (tone: Tone): Color =>
      tone === 'dim' ? P.dim : tone === 'danger' ? P.bad : tone === 'primary' ? (P.pillText ?? P.text) : P.text
    // Con foco (y paleta propia), el chip va en el acento sobre el fondo de
    // foco: se le pasan los colores ya intercambiados porque el engine invierte
    // el elemento enfocado.
    const chip = (text: string, tone: Tone = 'normal', key?: string) =>
      P.focusBg !== undefined && key !== undefined && e.props.isFocused && u.focus === key ? (
        <Text color={P.focusBg} backgroundColor={P.accent} weight="bold">
          {` ${text} `}
        </Text>
      ) : P.focusBg !== undefined ? (
        <Text
          backgroundColor={tone === 'primary' ? (P.pill ?? P.focusBg) : P.focusBg}
          color={toneColor(tone)}
          {...(tone === 'primary' ? { weight: 'bold' as const } : {})}
        >
          {` ${text} `}
        </Text>
      ) : tone === 'primary' ? (
        <Text inverse color={P.accent} weight="bold">
          {` ${text} `}
        </Text>
      ) : (
        <Text color={toneColor(tone)}>{`[${text}]`}</Text>
      )
    const header = (text: string) =>
      wrapWords(text, C).map((t, i) => (
        <Text key={`h-${i}`} color={P.accent} weight="bold">
          {t}
        </Text>
      ))
    // Texto partido por palabra en líneas de hasta C (nunca se trunca).
    const lines = (text: string, color: Color, prefix: string) =>
      wrapWords(text, C).map((t, i) => (
        <Text key={`${prefix}-${i}`} color={color}>
          {t}
        </Text>
      ))
    // Solo un elemento por pestaña arranca con el foco.
    let autoFocusTaken = false
    const takeFocus = () => {
      if (autoFocusTaken) return {}
      autoFocusTaken = true
      return { autoFocus: true as const }
    }

    // Pestañas. En fila (pane angosto): la activa como pastilla, el resto en
    // dim. En columna: una por línea, la activa con "▌" en el acento y el resto
    // en gris secundario.
    const short = W < 47
    const goTab = (id: Tab) =>
      fire(async () => {
        // El foco (y la pista) pasan a la primera fila de la pestaña.
        await update($, ui, (x): Panel4dUi => ({
          ...x,
          tab: id,
          focus: firstFocus(id),
          confirm: x.confirm === 'exit' ? 'exit' : undefined,
        }))
        await $.ui.focus({ requestId: PANE, key: firstFocus(id) }).catch(() => undefined)
      })
    const tabRows = pack(TABS, ([, label, brief]) => (short ? brief : label).length + 2, W, 1)
    const tabs = wide ? (
      <Box flexDirection="column" width={TAB_COL}>
        {TABS.map(([id, label]) => (
          <Button key={`tab-${id}`} plain onPress={goTab(id)}>
            {id === u.tab ? (
              <Text color={P.accent} weight="bold">
                {`▌ ${label}`.padEnd(TAB_COL)}
              </Text>
            ) : (
              <Text color={P.label}>{`  ${label}`.padEnd(TAB_COL)}</Text>
            )}
          </Button>
        ))}
      </Box>
    ) : (
      <Box flexDirection="column">
        {tabRows.map((r, i) => (
          <Box key={`tabs-${i}`} flexDirection="row" columnGap={1}>
            {r.map(([id, label, brief]) => (
              <Button key={`tab-${id}`} plain onPress={goTab(id)}>
                {id === u.tab ? pill(short ? brief : label) : <Text color={P.dim}>{` ${short ? brief : label} `}</Text>}
              </Button>
            ))}
          </Box>
        ))}
      </Box>
    )

    // El engine dibuja el Button con foco en INVERSE (fg y bg intercambiados),
    // sin prop para apagarlo. Para que la fila enfocada quede con fondo apagado
    // de borde a borde y texto claro, bajo el foco se le dan los colores ya
    // intercambiados: color = fondo de foco, backgroundColor = color del texto.
    // Sin paleta propia, un solo color para que el inverse quede parejo.
    const hasRing = e.props.isFocused
    const ink = (isFocused: boolean, fg: Color) =>
      !isFocused
        ? { color: fg }
        : P.focusBg !== undefined
          ? { color: P.focusBg, backgroundColor: fg }
          : { color: P.text }

    // Fila de ajuste: "▌ Etiqueta      ‹ valor › •" con sangría de 2 y el valor
    // en una columna fija de la pestaña (la etiqueta más larga + 2), no contra
    // el borde; el resto se rellena hasta C para que el fondo de foco cubra la fila.
    // Presupuesto de la fila: INDENT + col (etiqueta) + tail, donde tail =
    // "‹ " + valor + " ›" (4 + valor) + la marca de pendiente. El valor se
    // trunca con "…" solo si ni con la columna mínima entra.
    const labelOf = (s: Setting) => ROW_LABEL[s.id] ?? s.label
    const tabSettings = SETTINGS.filter(x => x.tab === u.tab)
    const labelCol = Math.max(0, ...tabSettings.map(s => labelOf(s).length)) + 2
    const row = (s: Setting) => {
      const isPending = pend.includes(s.id)
      const isFocused = hasRing && u.focus === s.id
      const mark = isPending ? ' •' : ''
      const full = shownOf(s, valueOf(u, s.id), u)
      const maxValue = Math.max(1, C - INDENT - 4 - mark.length - 3)
      const value = full.length > maxValue ? `${full.slice(0, maxValue - 1)}…` : full
      const tail = value.length + 4 + mark.length
      // La columna se achica solo si la fila no entra en W.
      const col = Math.max(2, Math.min(labelCol, C - INDENT - tail))
      const name = labelOf(s)
      const label = name.length > col - 1 ? `${name.slice(0, Math.max(1, col - 2))}…` : name
      const fill = ' '.repeat(Math.max(0, C - INDENT - col - tail))
      const bg = isFocused && P.focusBg !== undefined ? { backgroundColor: P.focusBg } : {}
      return (
        <Box key={`row-${s.id}`} {...bg}>
          <Button key={s.id} plain {...takeFocus()} onPress={fire(() => cycle($, s.id))}>
            <Text {...ink(isFocused, P.accent)} weight="bold">
              {isFocused ? '▌ ' : '  '}
            </Text>
            <Text {...ink(isFocused, isFocused ? P.accent : P.label)}>{label.padEnd(col)}</Text>
            <Text {...ink(isFocused, P.dim)}>‹ </Text>
            <Text {...ink(isFocused, isPending ? P.accent : P.text)} {...(isPending ? { weight: 'bold' as const } : {})}>
              {value}
            </Text>
            <Text {...ink(isFocused, P.dim)}> ›</Text>
            <Text {...ink(isFocused, P.accent)} weight="bold">
              {mark}
              {fill}
            </Text>
          </Button>
        </Box>
      )
    }

    // Filas de la pestaña, agrupadas por sección.
    // `rows`: filas que ocupan los items (sin título); por defecto, uno por item.
    // Sirve para dibujar el separador vertical al alto justo del contenido.
    const groups: { title: string; items: RenderChildren[]; rows?: number }[] = []
    for (const s of SETTINGS.filter(x => x.tab === u.tab)) {
      const title = SECTION_OF[s.id]
      const last = groups[groups.length - 1]
      if (last && last.title === title) last.items.push(row(s))
      else groups.push({ title, items: [row(s)] })
    }

    if (u.tab === 'sesion') {
      const act = (key: string) => {
        const a = ACTIONS[key]
        return a ? (
          <Button
            key={key}
            plain
            onPress={fire(async () =>
              key === 'act-clear'
                ? update($, ui, (x): Panel4dUi => ({ ...x, confirm: 'clear' }))
                : runAction($, key),
            )}
          >
            {chip(a.label, 'normal', key)}
          </Button>
        ) : null
      }
      const chipPack = (keys: string[]) => pack(keys, k => (ACTIONS[k]?.label.length ?? 0) + 2, C - INDENT, 1)
      const clearQ = wrapWords('¿Vaciar el contexto con /clear?', C - INDENT)
      const chipRows = (keys: string[]) => (
        <Box flexDirection="column" paddingLeft={INDENT}>
          {chipPack(keys).map((r, i) => (
            <Box key={`chips-${r[0] ?? i}`} flexDirection="row" columnGap={1}>
              {r.map(act)}
            </Box>
          ))}
        </Box>
      )
      groups.push({
        title: 'ACCIONES · CORREN YA',
        rows: u.confirm === 'clear' ? clearQ.length + 1 : chipPack(['act-compact', 'act-clear', 'act-handoff']).length,
        items: [
          u.confirm === 'clear' ? (
            <Box flexDirection="column" paddingLeft={INDENT}>
              {clearQ.map((t, i) => (
                <Text key={`clear-q-${i}`} color={P.warn}>
                  {t}
                </Text>
              ))}
              <Box flexDirection="row" columnGap={1} flexWrap="wrap">
                <Button
                  key="clear-yes"
                  plain
                  onPress={fire(async () => {
                    await update($, ui, (x): Panel4dUi => ({ ...x, confirm: undefined }))
                    await runAction($, 'act-clear')
                  })}
                >
                  {chip('Sí, limpiar', 'normal', 'clear-yes')}
                </Button>
                <Button
                  key="clear-no"
                  plain
                  onPress={fire(async () => {
                    await update($, ui, (x): Panel4dUi => ({ ...x, confirm: undefined }))
                    $.ui.toast('Panel 4D: /clear cancelado')
                  })}
                >
                  {chip('Cancelar', 'normal', 'clear-no')}
                </Button>
              </Box>
            </Box>
          ) : (
            chipRows(['act-compact', 'act-clear', 'act-handoff'])
          ),
        ],
      })
      groups.push({
        title: 'ATAJOS',
        rows: chipPack(['short-sentinel-audit', 'short-4d-status']).length,
        items: [
          chipRows(['short-sentinel-audit', 'short-4d-status']),
        ],
      })
    } else if (u.tab === 'perfiles') {
      groups.push({
        title: 'PERFILES · CARGAN EL BORRADOR',
        rows: Object.values(PROFILES).reduce((sum, pr) => sum + 1 + packSegments(pr.desc.split(' · '), C - 2).length, 0),
        items: (Object.keys(PROFILES) as ProfileName[]).map(name => {
          const key = `profile-${name}`
          const isFocused = hasRing && u.focus === key
          const bg = isFocused && P.focusBg !== undefined ? { backgroundColor: P.focusBg } : {}
          const pr = PROFILES[name]
          return (
            <Box key={`row-${key}`} flexDirection="column" {...bg}>
              <Button key={key} plain {...takeFocus()} onPress={fire(() => loadProfile($, name))}>
                <Text {...ink(isFocused, P.accent)} weight="bold">
                  {isFocused ? '▌ ' : '  '}
                </Text>
                <Text {...ink(isFocused, P.text)}>{pr.label.padEnd(C - 2)}</Text>
              </Button>
              {packSegments(pr.desc.split(' · '), C - 2).map((t, i) => (
                <Text key={`${key}-desc-${i}`} color={isFocused ? P.label : P.dim} {...bg}>
                  {`  ${t}`.padEnd(C)}
                </Text>
              ))}
            </Box>
          )
        }),
      })
    }

    // Una línea de ayuda. En un ajuste: solo el valor elegido ("Experto · todo
    // el detalle..."), el nombre en el acento y la descripción en gris; se
    // actualiza al ciclar. Si no, la del elemento con foco o la de la pestaña.
    const focused = u.focus !== undefined && isInTab(u.focus, u.tab) ? u.focus : ''
    const silent = valueOf(u, 'bar.quiet') === 'silencio'
    const focusedSetting = SETTING.get(focused)
    const cur = focusedSetting ? valueOf(u, focusedSetting.id) : undefined
    const shownName = focusedSetting && cur !== undefined ? shownOf(focusedSetting, cur, u) : ''
    const hintName = shownName ? `${shownName.charAt(0).toUpperCase()}${shownName.slice(1)}` : ''
    const hint = focusedSetting
      ? focusedSetting.id === 'bar.cut' && silent
        ? 'sin aviso: la barra está en silencio'
        : ((cur !== undefined ? focusedSetting.about?.[cur] : undefined) ?? focusedSetting.hint)
      : (ACTIONS[focused]?.hint ??
        FOCUS_HINT[focused] ??
        (focused.startsWith('profile-')
          ? `Carga ${PROFILES[focused.slice(8) as ProfileName]?.label ?? ''} en el borrador`
          : TAB_HINT[u.tab]))
    const hintLine = hintName ? `${hintName} · ${hint}` : `${hint.charAt(0).toUpperCase()}${hint.slice(1)}`

    // Pie: estado de cambios + botones + teclas, justo debajo del contenido.
    // No se ancla al fondo: `scroll.bodyRows` es el alto máximo del cuerpo, no
    // las filas visibles, y un espaciador lo empujaba fuera de la ventana.
    const keys =
      u.confirm === 'exit'
        ? fit(W, 'Tab/↑↓ mover · Enter elegir', 'Enter elegir')
        : fit(
            W,
            'Tab/↑↓ mover · Enter cambia · Esc salir',
            '↑↓ mover · Enter cambia · Esc salir',
            'Enter cambia · Esc salir',
          )
    // Botones a la DERECHA en orden de modal (el primario al final) y el
    // estado a la izquierda en la misma línea; si no entra, el estado arriba.
    const bar = (status: RenderChildren, statusWidth: number, chips: RenderChildren[], chipsWidth: number) => {
      const buttons = (
        <Box flexDirection="row" columnGap={2} flexWrap="wrap">
          {chips}
        </Box>
      )
      return statusWidth + 2 + chipsWidth <= W ? (
        <Box flexDirection="row" justifyContent="space-between" width={W}>
          {status}
          {buttons}
        </Box>
      ) : (
        <Box flexDirection="column" width={W}>
          {status}
          <Box flexDirection="row" justifyContent="flex-end" width={W}>
            {buttons}
          </Box>
        </Box>
      )
    }
    const chipW = (...labels: string[]) =>
      labels.reduce((sum, t) => sum + t.length + 2, 0) + 2 * (labels.length - 1)
    let footer: RenderChildren
    if (u.confirm === 'exit') {
      const cw = chipW('Volver', 'Descartar y salir')
      const text = fit(
        W - cw - 2,
        `Hay ${n} cambio${n === 1 ? '' : 's'} sin guardar`,
        `${n} sin guardar`,
      )
      footer = bar(
        <Text color={P.warn} wrap="truncate-end">
          {text}
        </Text>,
        text.length,
        [
          <Button key="back" plain onPress={fire(() => update($, ui, (x): Panel4dUi => ({ ...x, confirm: undefined })))}>
            {chip('Volver', 'primary', 'back')}
          </Button>,
          <Button key="discard" plain onPress={fire(() => closePane($))}>
            {chip('Descartar y salir', 'danger', 'discard')}
          </Button>,
        ],
        cw,
      )
    } else {
      const cw = chipW('Salir', 'Guardar y salir', 'Guardar')
      const plural = n === 1 ? '' : 's'
      const text = u.busy
        ? 'Guardando…'
        : n > 0
          ? fit(W - cw - 2, `• ${n} cambio${plural} sin guardar`, `• ${n} sin guardar`)
          : fit(W - cw - 2, 'Sin cambios pendientes', 'Sin cambios')
      footer = bar(
        n > 0 || u.busy ? (
          <Text color={P.accent} weight="bold" wrap="truncate-end">
            {text}
          </Text>
        ) : (
          <Text color={P.dim} wrap="truncate-end">
            {text}
          </Text>
        ),
        text.length,
        [
          <Button key="exit" plain role="dismiss" onPress={fire(() => exitPane($))}>
            {chip('Salir', 'normal', 'exit')}
          </Button>,
          <Button
            key="save-exit"
            plain
            onPress={fire(async () => {
              if (await save($)) await closePane($)
            })}
          >
            {chip('Guardar y salir', 'normal', 'save-exit')}
          </Button>,
          <Button key="save" plain onPress={fire(() => save($))}>
            {chip('Guardar', n > 0 ? 'primary' : 'dim', 'save')}
          </Button>,
        ],
        cw,
      )
    }

    // Contenido (secciones y ayuda): a la derecha de las pestañas en
    // columna, o debajo de las pestañas en fila. Mide C de ancho.
    const hintSingle = hintName !== '' && hintLine.length <= C
    const hintLines = hintSingle ? 1 : wrapWords(hintLine, C).length
    const noteLines = u.note !== undefined ? wrapWords(u.note, C).length : 0
    // Ritmo vertical: la primera sección arranca en la primera fila (a la par de
    // la primera pestaña); 1 línea vacía entre secciones, 1 antes de la ayuda y
    // 1 antes de la línea del pie, nunca 2 seguidas.
    // Filas del contenido, para que el separador vertical llegue justo hasta abajo.
    const bodyRows =
      groups.reduce(
        (sum, g, i) => sum + (i === 0 ? 0 : 1) + wrapWords(g.title, C).length + (g.rows ?? g.items.length),
        0,
      ) +
      1 +
      hintLines +
      noteLines
    // En columna, el separador sigue por la línea vacía de antes del pie y se une
    // con la línea horizontal en ┴.
    const sepRows = Math.max(TABS.length, bodyRows) + 1
    const footRule = wide ? (
      <Text color={P.rule ?? P.dim}>{`${'─'.repeat(TAB_COL)}┴${'─'.repeat(Math.max(0, W - TAB_COL - 1))}`}</Text>
    ) : (
      rule
    )
    const body = (
      <Box flexDirection="column" width={C}>
        {groups.map((g, i) => (
          <Box key={`sec-${i}`} flexDirection="column" marginTop={i === 0 ? 0 : 1}>
            {header(g.title)}
            {g.items}
          </Box>
        ))}
        <Box marginTop={1} flexDirection="column">
          {hintSingle ? (
            <Box key="hint-row" flexDirection="row">
              <Text color={P.accent}>{hintName}</Text>
              <Text color={P.label}>{` · ${hint}`}</Text>
            </Box>
          ) : (
            lines(hintLine, P.label, 'hint')
          )}
        </Box>
        {u.note !== undefined && lines(u.note, P.accent, 'note')}
      </Box>
    )

    return (
      // Margen de 1 línea arriba (lejos de la X de cerrar) y 1 columna a la izquierda.
      <Box flexDirection="column" width={W} marginTop={1} marginLeft={1}>
        {wide ? (
          // Dos columnas: pestañas | separador tenue | contenido.
          <Box key="cols" flexDirection="row">
            {tabs}
            <Box key="sep" flexDirection="column" width={1}>
              {Array.from({ length: sepRows }, (_, i) => (
                <Text key={`sep-${i}`} color={P.rule ?? P.dim}>
                  │
                </Text>
              ))}
            </Box>
            <Box flexDirection="column" width={C} marginLeft={1}>
              {body}
            </Box>
          </Box>
        ) : (
          <Box key="rows" flexDirection="column">
            {tabs}
            {rule}
            {body}
          </Box>
        )}
        {/* Pie a lo ancho completo, debajo de ambas columnas. En columna, la
            línea vacía de antes del pie ya la pone el separador. */}
        <Box marginTop={wide ? 0 : 1} flexDirection="column">
          {footRule}
          {footer}
          {packSegments(keys.split(' · '), W).map((t, i) => (
            <Text key={`keys-${i}`} color={P.dim} wrap="truncate-end">
              {t}
            </Text>
          ))}
        </Box>
      </Box>
    )
  })

  // Esfuerzo y modelo en uso, tal como sale cada pedido del hilo principal
  // (los subagentes, con agentId, se ignoran: tienen su propio modelo). Solo
  // escribe el atom si algo cambió, no en cada paso.
  on('turn.step', async function* ($, e, next) {
    if (e.agentId === undefined) {
      const effort = e.effort === undefined ? undefined : String(e.effort)
      const now = await read($, live)
      if (now.effort !== effort || now.model !== e.model) {
        await update($, live, l => ({ ...l, model: e.model, effort: effort ?? l.effort }))
      }
    }

    return yield* next(e)
  })

  // Al cerrar cada turno: uso de contexto, aviso de plan 5h y
  // valores reales del pane al día (el borrador no se toca).
  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId !== undefined) return done
    try {
      const at = await $.clock.now()
      await update($, live, l => ({ ...l, lastTurnAt: at }))
      const l = await refreshUsage($)
      const p = await read($, prefs)
      if (
        p.notify &&
        typeof l.fiveHour === 'number' &&
        l.fiveHour >= 90 &&
        planToastFor !== (l.fiveHourResetsAt ?? 'sin-reset')
      ) {
        planToastFor = l.fiveHourResetsAt ?? 'sin-reset'
        const back = hhmm(l.fiveHourResetsAt)
        $.ui.toast(`Plan 5h al ${l.fiveHour}%${back ? ` (vuelve ${back})` : ''}`)
      }
      const panes = await $.ui.panes()
      if (panes.some(x => x.id === PANE)) {
        // Si en el medio hubo (o hay) un guardado, esta foto es vieja: se descarta.
        const seq = saveSeq
        const snap = await loadSnapshot($)
        await update($, ui, (u): Panel4dUi => (u.busy || saveSeq !== seq ? u : { ...u, ...snap }))
      }
    } catch {
      // best-effort
    }

    return done
  })
}
