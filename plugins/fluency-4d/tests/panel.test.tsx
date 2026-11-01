import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const HOME = '/home/t'
const DIR = `${HOME}/.claude/fluency4d`
const PANE_ID = 'panel-4d'
const PLUGIN = 'fluency-4d'

// El engine entrega rutas absolutas del sistema (\ y unidad en Windows: /home/t
// puede llegar con letra de unidad); se normalizan para que el home falso sea neutro.
const slash = (path: string) => path.replace(/\\/g, '/').replace(/^[A-Za-z]:(?=\/)/, '')

// /panel como si lo tipeara la persona (el evento trae el nombre
// registrado, sin namespace).
const panel = (args = '') => ({
  command: 'panel',
  args,
  origin: { kind: 'composer' as const },
  presentation: { isFullscreen: true, columns: 140 },
})

const paneProps = (bodyColumns = 60, placement: 'dock' | 'inline' = 'dock') => ({
  title: 'Panel 4D',
  isFocused: true,
  bodyColumns,
  placement,
  scroll: { offset: 0, bodyRows: 40 },
  view: {},
})

// Nada hay debajo del plugin: estos hooks hacen de engine (archivos, comandos,
// uso, /config, settings y el pane).
function engine(
  on: On,
  settings: Record<string, unknown> = {},
  opts: {
    resetsAt?: string
    fiveHour?: number
    denyTheme?: string
    failCommand?: string
    holdCommand?: Promise<void>
    env?: Record<string, string>
  } = {},
) {
  const files: Record<string, string> = {
    [`${DIR}/statusline.json`]: '{"mode":"experto","quiet":false,"theme":"nord","extra":1}\n',
    [`${DIR}/adhd.json`]: '{"on": false, "level": "lite"}',
    [`${DIR}/caveman.json`]: '{"on": true, "level": "ultra"}',
    [`${DIR}/panel4d.json`]: '{}',
  }
  const ran: string[] = []
  const toasts: string[] = []
  const opened: unknown[] = []
  const closed: string[] = []
  const configSet: unknown[] = []
  let isOpen = false

  mock.env(on, opts.env ?? { USERPROFILE: HOME })
  const clock = mock.clock(on)
  // Lecturas y escrituras ceden el turno, para que dos cambios en paralelo se crucen.
  const tick = async () => {
    for (let i = 0; i < 5; i++) await Promise.resolve()
  }
  on('fs.exists', (_, e) => {
    const path = slash(e.path)
    return { value: path in files || Object.keys(files).some(f => f.startsWith(`${path}/`)) }
  })
  on('fs.list', (_, e) => {
    const dir = slash(e.path)
    const names = Object.keys(files)
      .filter(f => f.startsWith(`${dir}/`) && !f.slice(dir.length + 1).includes('/'))
      .map(f => f.slice(dir.length + 1))
    return {
      value: names.map(name => ({
        name,
        kind: 'file' as const,
        size: (files[`${dir}/${name}`] ?? '').length,
        mtimeMs: 0,
        isLink: false,
      })),
    }
  })
  on('fs.read', async (_, e) => {
    await tick()
    const text = files[slash(e.path)]
    if (text === undefined) throw new Error('ENOENT')
    return { value: text }
  })
  on('fs.write', async (_, e) => {
    await tick()
    files[slash(e.path)] = e.text
    return { value: undefined }
  })
  on('command.list', () => ({
    value: ['effort', 'model', 'fast', 'autocompact', 'compact', 'clear'].map(name => ({
      name,
      description: name,
      source: 'builtin' as const,
    })),
  }))
  on('command.run', async (_, e) => {
    if (opts.holdCommand !== undefined) await opts.holdCommand
    // Un comando que falla: el hook se salta y nada debajo contesta (rechaza).
    if (e.command === opts.failCommand) throw new Error('no se pudo')
    ran.push(`${e.command} ${e.args}`.trim())
    return { text: '' }
  })
  on('ui.log', () => ({ value: undefined }))
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.open', (_, e) => {
    opened.push(e)
    isOpen = true
    return { value: { isPlaced: true } }
  })
  on('ui.close', (_, e) => {
    closed.push(`${e.id}:${e.origin.kind}`)
    isOpen = false
    return { value: undefined }
  })
  on('ui.panes', () => ({
    value: isOpen
      ? [{ id: PANE_ID, title: 'Panel 4D', isShown: true, isFocused: true, isPlaced: true }]
      : [],
  }))
  const focused: string[] = []
  on('ui.focus', (_, e) => {
    focused.push(String(e.element))
    // Una llamada en $ se contesta { value }.
    return { value: {} } as never
  })
  on('session.usage', () => ({
    value: {
      startedAt: 0,
      context: { tokens: 50_000, window: 200_000, percent: 25 },
      rateLimits: [
        { kind: 'five_hour', percentUsed: opts.fiveHour ?? 40, resetsAt: opts.resetsAt },
      ],
    },
  }))
  on('session.model', () => ({ value: 'claude-opus-5-5' }))
  on('settings.read', () => ({ value: settings as never }))
  on('config.list', () => ({
    value: [
      {
        key: 'theme',
        label: 'Theme',
        kind: 'choice',
        value: 'dark',
        options: ['dark', 'light', 'dark-daltonized'],
        provider: { plugin: 'engine', tier: 'core' },
        isLocked: false,
      } as never,
    ],
  }))
  on('config.set', (_, e) => {
    if (opts.denyTheme !== undefined) return { deny: opts.denyTheme }
    configSet.push({ key: e.key, value: e.value })
    return { value: e.value }
  })

  const json = (name: string) => JSON.parse(files[`${DIR}/${name}.json`] ?? '{}')

  return { files, ran, toasts, opened, closed, configSet, focused, json, clock }
}

const SURFACES = ['terminal', 'desktop'] as const

test('/panel abre el pane con pestañas, filas alineadas y pie de 3 botones', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel())

  expect(eng.opened[0]).toMatchObject({
    id: PANE_ID,
    title: 'Panel 4D',
    focus: true,
    closeOnEscape: true,
    columns: 64,
  })
  for (const [surface, cols, placement] of [
    ['terminal', 60, 'dock'],
    ['terminal', 46, 'dock'],
    ['terminal', 120, 'inline'],
    ['desktop', 60, 'dock'],
  ] as const) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface,
      props: paneProps(cols, placement),
    })
    for (const id of ['barra', 'modelo', 'modos', 'sesion', 'perfiles']) {
      expect(await ui.find({ type: 'Button', key: `tab-${id}` })).toBeDefined()
    }
    for (const key of ['save', 'save-exit', 'exit']) {
      expect(await ui.find({ type: 'Button', key })).toBeDefined()
    }
    const mode = await ui.find({ type: 'Button', key: 'bar.mode' })
    expect(mode?.text).toMatch(/^[▌ ] Modo +‹ experto › *$/)
    // Cada fila ocupa el ancho del cuerpo (tope 60) menos 1 de margen derecho.
    // Margen de 1 a cada lado; desde 58 columnas las pestañas van en columna (11 + separador + 1 de aire).
    expect(mode?.text.length).toBe(Math.min(cols, 60) - 2 - (cols >= 58 ? 13 : 0))
    expect(mode?.text).not.toMatch(/·/)
    expect((await ui.find({ type: 'Button', key: 'claude.theme' }))?.text).toMatch(/‹ dark ›/)
    expect(await ui.find({ type: 'Text', text: /^Sin cambios/ })).toBeDefined()
    await ui.unmount()
  }
})

test('sin statusline.json el panel muestra los defaults de la barra (experto, templado, silencio) y no escribe de más', async ($, on) => {
  const eng = engine(on)
  delete eng.files[`${DIR}/statusline.json`]
  await $.command.run(panel('barra'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  expect((await ui.find({ type: 'Button', key: 'bar.mode' }))?.text).toMatch(/‹ experto › *$/)
  expect((await ui.find({ type: 'Button', key: 'bar.theme' }))?.text).toMatch(/‹ templado › *$/)
  expect((await ui.find({ type: 'Button', key: 'bar.quiet' }))?.text).toMatch(/‹ silencio › *$/)
  expect(await ui.find({ type: 'Text', text: /^Sin cambios/ })).toBeDefined()
  // Guardar sin cambios no crea el archivo.
  await ui.press({ key: 'save' })
  expect(`${DIR}/statusline.json` in eng.files).toBe(false)
  // Cambiar solo el modo escribe solo el modo (los defaults no se materializan).
  await ui.press({ key: 'bar.mode' }) // experto -> simple
  await ui.press({ key: 'save' })
  expect(eng.json('statusline')).toEqual({ mode: 'simple' })
  await ui.unmount()

  // Archivo con claves faltantes: cada una cae a su default.
  eng.files[`${DIR}/statusline.json`] = '{"cutFraction":0.25}'
  await $.command.run(panel('barra'))
  const ui2 = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  expect((await ui2.find({ type: 'Button', key: 'bar.mode' }))?.text).toMatch(/‹ experto › *$/)
  expect((await ui2.find({ type: 'Button', key: 'bar.theme' }))?.text).toMatch(/‹ templado › *$/)
  expect((await ui2.find({ type: 'Button', key: 'bar.quiet' }))?.text).toMatch(/‹ silencio › *$/)
  await ui2.unmount()
})

test('cambiar un valor NO escribe hasta Guardar; Guardar escribe y preserva claves ajenas', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('barra'))
  const before = eng.files[`${DIR}/statusline.json`]
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface,
      props: paneProps(),
    })
    await ui.press({ key: 'bar.mode' }) // experto -> simple
    await ui.press({ key: 'bar.theme' }) // nord -> gruvbox
    await ui.press({ key: 'bar.cut' }) // 50% -> 75%
    await ui.press({ key: 'bar.quiet' }) // avisos -> silencio
    expect(eng.files[`${DIR}/statusline.json`]).toBe(before)
    expect((await ui.find({ type: 'Button', key: 'bar.mode' }))?.text).toMatch(/^[▌ ] Modo +‹ simple › • *$/)
    expect(await ui.find({ type: 'Text', text: /• 4 (cambios )?sin guardar/ })).toBeDefined()

    // Dos Guardar a la vez: uno solo aplica, sin lost update.
    await Promise.all([ui.press({ key: 'save' }), ui.press({ key: 'save' })])
    expect(eng.json('statusline')).toEqual({
      mode: 'simple',
      quiet: true,
      theme: 'gruvbox',
      extra: 1,
      cutFraction: 0.75,
    })
    expect(eng.toasts.at(-1)).toMatch(/guardado: Modo simple, Tema de la barra gruvbox/)
    expect(await ui.find({ type: 'Text', text: /^Sin cambios/ })).toBeDefined()
    expect((await ui.find({ type: 'Button', key: 'bar.mode' }))?.text).toMatch(/^[▌ ] Modo +‹ simple › *$/)
    expect(eng.closed).toEqual([])
    await ui.unmount()
    // Vuelve al estado inicial para la otra superficie.
    eng.files[`${DIR}/statusline.json`] = before ?? ''
    await $.command.run(panel('barra'))
  }
})

test('Guardar y salir aplica preferencias y comandos y cierra el pane', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('sesion'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'notify.ttl' }) // 5 -> 60
  await ui.press({ key: 'session.autocompact' }) // sin dato -> 200000
  expect(eng.ran).toEqual([])
  await ui.press({ key: 'save-exit' })

  expect(eng.json('panel4d')).toEqual({ cacheTtlMin: 60 })
  expect(eng.ran).toEqual(['autocompact 200000'])
  expect(eng.closed).toEqual([`${PANE_ID}:plugin`])
  await ui.unmount()
})

test('Salir con pendientes pide confirmación; Descartar no escribe', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('modos'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'mode.verify' })
  await ui.press({ key: 'exit' })
  expect(eng.closed).toEqual([])
  expect(await ui.find({ type: 'Text', text: /(Hay 1 cambio|1) sin guardar/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', key: 'save' })).toBeUndefined()

  await ui.press({ key: 'back' })
  expect(await ui.find({ type: 'Button', key: 'save' })).toBeDefined()

  // (Esc = ui.close con origin person: el kit de tests no lo puede levantar.)
  await ui.press({ key: 'exit' })
  await ui.press({ key: 'discard' })
  expect(eng.closed).toEqual([`${PANE_ID}:plugin`])
  expect(eng.files[`${DIR}/verify.json`]).toBeUndefined()
  expect(eng.ran).toEqual([])
  await ui.unmount()
})

test('sin pendientes, Salir cierra directo y el próximo /panel arranca limpio', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel())
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'exit' })
  expect(eng.closed).toEqual([`${PANE_ID}:plugin`])
  await ui.unmount()
  await $.command.run(panel())
  const again = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  expect(await again.find({ type: 'Text', text: /^Sin cambios/ })).toBeDefined()
  await again.unmount()
})

test('un perfil carga el borrador sin escribir; Guardar lo aplica', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('perfiles'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  const before = { ...eng.files }
  await ui.press({ key: 'profile-foco' })
  expect(eng.files).toEqual(before)
  expect(eng.ran).toEqual([])
  expect(await ui.find({ type: 'Text', text: /Perfil Foco en el borrador \(5 pendientes\)/ })).toBeDefined()

  await ui.press({ key: 'save' })
  expect(eng.json('statusline')).toEqual({ mode: 'simple', quiet: true, theme: 'nord', extra: 1 })
  expect(eng.json('adhd')).toEqual({ on: true, level: 'lite' })
  expect(eng.json('caveman')).toEqual({ on: false, level: 'ultra' })
  expect(eng.ran).toEqual(['effort medium'])
  await ui.unmount()
})

test('perfil Ahorro corre los tres comandos al guardar', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('perfiles'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'desktop',
    props: paneProps(),
  })
  await ui.press({ key: 'profile-ahorro' })
  await ui.press({ key: 'save' })
  expect(eng.ran).toEqual(['effort low', 'fast off', 'autocompact 400000'])
  await ui.unmount()
})

test('verify-diff y ADHD/Caveman excluyentes al guardar', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('4d'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'mode.adhd' }) // off -> auto: Caveman pasa a off en el borrador
  expect((await ui.find({ type: 'Button', key: 'mode.caveman' }))?.text).toMatch(/^[▌ ] Caveman +‹ off › • *$/)
  await ui.press({ key: 'mode.verify' })
  await ui.press({ key: 'save' })

  expect(eng.json('adhd')).toEqual({ on: true, level: 'auto' })
  expect(eng.json('caveman')).toEqual({ on: false, level: 'ultra' })
  expect(eng.json('verify')).toEqual({ on: true })
  await ui.unmount()
})

test('el esfuerzo actual sale de modelSettings, que pisa al global', async ($, on) => {
  engine(on, {
    effortLevel: 'high',
    modelSettings: { 'claude-opus-5-5': { effortLevel: 'medium' } },
  })
  await $.command.run(panel('modelo'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  expect((await ui.find({ type: 'Button', key: 'model.effort' }))?.text).toMatch(/‹ medium › *$/)
  expect((await ui.find({ type: 'Button', key: 'model.model' }))?.text).toMatch(/‹ opus › *$/)
  await ui.unmount()
})

test('la fila Tema de Claude aplica config.set solo al Guardar', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('barra'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'claude.theme' }) // dark -> light
  expect(eng.configSet).toEqual([])
  expect((await ui.find({ type: 'Button', key: 'claude.theme' }))?.text).toMatch(/‹ light ›( •)? *$/)
  await ui.press({ key: 'save' })
  expect(eng.configSet).toEqual([{ key: 'theme', value: 'light' }])
  await ui.unmount()
})

test('el pane se pinta con la paleta del tema de la barra (templado = acento claude del tema)', async ($, on) => {
  const eng = engine(on)
  eng.files[`${DIR}/statusline.json`] = '{"mode":"normal","quiet":true,"theme":"templado"}'
  await $.command.run(panel())
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  // Acento puntual: los colores salen del tema de Claude (claves), solo los
  // fondos van en hex; el naranja es la clave `claude`, nunca un hex.
  const colors = (await ui.findAll({ type: 'Text' })).map(t => t.props.color)
  expect(colors.filter(c => !/^(text|inactive|subtle|claude|promptBorder|success|warning|error|#2e2a26|#201d1a)$/.test(String(c)))).toEqual([])
  expect(JSON.stringify(await ui.drawn())).not.toMatch(/d97757/i)
  // Acento en la pestaña activa y en los títulos de sección; separador tenue.
  const active = await ui.find({ type: 'Button', key: 'tab-barra' })
  expect(active?.text).toMatch(/^▌ Barra/)
  expect(JSON.stringify(active?.children)).toMatch(/"color":"claude","weight":"bold"/)
  expect((await ui.find({ type: 'Text', text: 'BARRA DE ESTADO' }))?.props.color).toBe('claude')
  expect((await ui.find({ type: 'Text', text: /^[─┴]+$/ }))?.props.color).toBe('promptBorder')
  // Foco en el acento: la fila enfocada va con los colores ya intercambiados.
  await ui.press({ key: 'tab-modelo' })
  const effort = await ui.find({ type: 'Button', key: 'model.effort' })
  expect(effort?.text).toMatch(/^▌ Esfuerzo/)
  expect(JSON.stringify(effort?.children)).toMatch(/"color":"#201d1a","backgroundColor":"claude"/)
  await ui.unmount()

  // Sin tema de barra: claves del tema de Claude.
  eng.files[`${DIR}/statusline.json`] = '{"mode":"normal"}'
  await $.command.run(panel())
  const ui2 = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui2.press({ key: 'tab-barra' })
  const tab = await ui2.find({ type: 'Button', key: 'tab-barra' })
  expect(JSON.stringify(tab?.children)).toMatch(/"color":"claude"/)
  await ui2.unmount()
})

test('un JSON roto no se pisa: el guardado avisa la falla', async ($, on) => {
  const eng = engine(on)
  eng.files[`${DIR}/statusline.json`] = '{"mode": "experto", roto'
  await $.command.run(panel('barra'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'bar.mode' })
  await ui.press({ key: 'save' })
  expect(eng.files[`${DIR}/statusline.json`]).toBe('{"mode": "experto", roto')
  expect(eng.toasts.at(-1)).toMatch(/guardado a medias\. Falló: Modo .*JSON inválido/)
  await ui.unmount()
})

test('un atajo a un comando que no existe falla suave', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('sesion'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'short-sentinel-audit' })
  expect(eng.ran).toEqual([])
  expect(eng.toasts.at(-1)).toMatch(/no está disponible/)
  await ui.unmount()
})

test('/clear pide confirmación en el pane antes de correr', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('sesion'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'act-clear' })
  expect(eng.ran).toEqual([])
  await ui.press({ key: 'clear-no' })
  expect(eng.ran).toEqual([])
  expect(eng.toasts.at(-1)).toMatch(/cancelado/)

  await ui.press({ key: 'act-clear' })
  await ui.press({ key: 'clear-yes' })
  expect(eng.ran).toEqual(['clear'])

  await ui.press({ key: 'act-compact' })
  expect(eng.ran).toEqual(['clear', 'compact'])
  await ui.unmount()
})

test('layout: pie al fondo del dock, filas al ancho justo, ayuda y teclas en una línea', async ($, on) => {
  engine(on)
  await $.command.run(panel('barra'))
  for (const [cols, placement] of [
    [44, 'dock'],
    [60, 'dock'],
    [90, 'inline'],
  ] as const) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(cols, placement),
    })
    const W = Math.min(cols, 60) - 2
    // El pie va justo debajo del contenido: sin alto mínimo ni espaciador.
    const root = await ui.drawn()
    expect((root as { props: Record<string, unknown> }).props.minHeight).toBeUndefined()
    expect(await ui.find({ type: 'Box', key: 'spacer' })).toBeUndefined()
    // Secciones con rótulo.
    expect(await ui.find({ type: 'Text', text: 'BARRA DE ESTADO' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'CLAUDE' })).toBeDefined()
    // Ninguna fila ni línea de texto se parte: todas entran en W.
    const wide = (await ui.findAll({ type: 'Button' }))
      .filter(b => !b.key?.startsWith('tab-') && b.text.length > W)
      .map(b => `${b.key}=${JSON.stringify(b.text)}`)
    expect(wide).toEqual([])
    const keys = await ui.find({ type: 'Text', text: /Esc salir/ })
    expect(keys?.text.length).toBeLessThanOrEqual(W)
    expect(keys?.text).not.toMatch(/[↺]/)
    expect(keys?.props.wrap).toBe('truncate-end')
    const tabsWidth = (await ui.findAll({ type: 'Button' }))
      .filter(b => b.key?.startsWith('tab-'))
      .reduce((sum, b) => sum + b.text.length + 1, -1)
    // En fila (sin columna de pestañas) la fila de pestañas entra en W.
    if (!(await ui.find({ type: 'Box', key: 'cols' }))) expect(tabsWidth).toBeLessThanOrEqual(W)
    // Pie: chips a la derecha en orden de modal (Salir, Guardar y salir, Guardar);
    // el estado a la izquierda en la misma línea si entra, si no arriba.
    const order = (await ui.findAll({ type: 'Button' }))
      .map(b => b.key)
      .filter(k => k === 'exit' || k === 'save-exit' || k === 'save')
    expect(order).toEqual(['exit', 'save-exit', 'save'])
    const sameLine = await ui.find({ type: 'Box', text: /Sin cambios.*Salir.*Guardar y salir.*Guardar/ })
    const inline = (await ui.findAll({ type: 'Box' })).some(
      b => b.props.justifyContent === 'space-between',
    )
    expect(inline).toBe(W >= 50)
    if (!inline) {
      expect((await ui.findAll({ type: 'Box' })).some(b => b.props.justifyContent === 'flex-end')).toBe(true)
    }
    expect(sameLine).toBeDefined()
    // Sin cambios, el chip de Guardar va apagado (sigue siendo chip); con cambios, primario.
    const saveChip = async () => JSON.stringify((await ui.find({ type: 'Button', key: 'save' }))?.children)
    expect(await saveChip()).toMatch(/"backgroundColor":"#3b4252","color":"#4c566a"/)
    await ui.press({ key: 'bar.mode' })
    expect(await saveChip()).toMatch(/"backgroundColor":"#4c566a","color":"#eceff4","weight":"bold"/)
    await ui.press({ key: 'bar.mode' })
    await ui.press({ key: 'bar.mode' })
    await ui.unmount()
  }
})

// Filas que ocupa un árbol dibujado (aprox. del terminal: una línea por Text o
// Button, columnas apiladas, filas lado a lado, más los marginTop).
type Node = { type?: string; props?: Record<string, unknown>; children?: unknown[] }
function rowsOf(n: unknown): number {
  if (n === null || typeof n !== 'object') return 0
  const node = n as Node
  const margin = Number(node.props?.marginTop ?? 0)
  if (node.type === 'Text' || node.type === 'Button') return 1 + margin
  const kids = (node.children ?? []).map(rowsOf)
  const inner =
    node.props?.flexDirection === 'column'
      ? kids.reduce((a, b) => a + b, 0)
      : Math.max(0, ...kids)
  return inner + margin
}

test('el pie (estado, 3 botones, teclas) entra en un dock de 25 filas en cada pestaña', async ($, on) => {
  engine(on)
  await $.command.run(panel())
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: { ...paneProps(60), scroll: { offset: 0, bodyRows: 25 } },
  })
  for (const tab of ['barra', 'modelo', 'modos', 'sesion', 'perfiles']) {
    await ui.press({ key: `tab-${tab}` })
    expect(rowsOf(await ui.drawn())).toBeLessThanOrEqual(25)
    expect(await ui.find({ type: 'Text', text: /^Sin cambios/ })).toBeDefined()
    for (const key of ['save', 'save-exit', 'exit']) {
      expect(await ui.find({ type: 'Button', key })).toBeDefined()
    }
    expect(await ui.find({ type: 'Text', text: /Esc salir/ })).toBeDefined()
  }
  await ui.unmount()
})

test('cambiar de pestaña lleva el foco (y la pista) a su primera fila', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel())
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(60),
  })
  await ui.press({ key: 'tab-modelo' })
  expect(await ui.find({ type: 'Text', text: /razona/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /simple: semáforo/ })).toBeUndefined()
  expect((await ui.find({ type: 'Button', key: 'model.effort' }))?.text).toMatch(/^▌/)

  await ui.press({ key: 'tab-perfiles' })
  const foco = await ui.find({ type: 'Button', key: 'profile-foco' })
  expect(foco?.text).toMatch(/^▌ Foco/)
  // Bajo el foco la fila lleva los colores ya intercambiados (el engine la invierte).
  // (tema nord: fondo de foco #3b4252, texto #eceff4).
  expect(JSON.stringify(foco?.children)).toMatch(/"color":"#3b4252","backgroundColor":"#eceff4"/)
  expect(await ui.find({ type: 'Text', text: /barra simple en silencio/ })).toBeDefined()
  expect(eng.ran).toEqual([])
  await ui.unmount()
})

test('sin línea de estado arriba: el contenido arranca con la primera sección', async ($, on) => {
  engine(on, {}, { fiveHour: 11, resetsAt: '2026-10-31T03:00:00' })
  await $.command.run(panel())
  for (const cols of [60, 45]) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(cols),
    })
    for (const tab of ['barra', 'modelo', 'modos', 'sesion', 'perfiles']) {
      await ui.press({ key: `tab-${tab}` })
      const texts = (await ui.findAll({ type: 'Text' })).map(t => t.text)
      expect(texts.filter(t => /ctx \d+%|plan 5h|vuelve \d|^esfuerzo |caché ~|caché fría/.test(t))).toEqual([])
    }
    const root = (await ui.drawn()) as unknown as Node
    expect(root.props?.marginTop).toBe(1)
    await ui.unmount()
  }
})

test('un tema custom de ~/.claude/themes aparece como "custom:<slug>" y se aplica al guardar', async ($, on) => {
  const eng = engine(on)
  eng.files[`${HOME}/.claude/themes/templado.json`] =
    '{"name":"Templado","base":"dark","overrides":{"text":"#c4c4c4"}}'
  eng.files[`${HOME}/.claude/themes/notas.txt`] = 'no es un tema'
  await $.command.run(panel('barra'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  // dark -> light -> dark-daltonized -> Templado
  for (let i = 0; i < 3; i++) await ui.press({ key: 'claude.theme' })
  expect((await ui.find({ type: 'Button', key: 'claude.theme' }))?.text).toMatch(/‹ Templado ›( •)? *$/)
  expect(eng.configSet).toEqual([])
  await ui.press({ key: 'save' })
  expect(eng.configSet).toEqual([{ key: 'theme', value: 'custom:templado' }])
  await ui.unmount()
})

test('si /config rechaza el tema, el toast dice el motivo exacto', async ($, on) => {
  const reason = 'Theme doesn’t accept "custom:templado". For custom themes, use /theme.'
  const eng = engine(on, {}, { denyTheme: reason })
  eng.files[`${HOME}/.claude/themes/templado.json`] = '{"name":"Templado","base":"dark"}'
  await $.command.run(panel('barra'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  for (let i = 0; i < 3; i++) await ui.press({ key: 'claude.theme' })
  await ui.press({ key: 'save' })
  expect(eng.toasts.at(-1)).toContain(`Tema de Claude Templado (${reason})`)
  await ui.unmount()
})

// Una confirmación como máximo por acción: cuenta cuántas veces se ve la fila
// "Descartar y salir" a lo largo de los pasos, y cuántas veces se cierra el pane.
test('una sola confirmación por acción del pie (0 o 1) y el pane se cierra', async ($, on) => {
  const eng = engine(on)
  const mount = () =>
    $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(),
    })
  let confirms = 0
  const seen = async (ui: Awaited<ReturnType<typeof mount>>) => {
    if (await ui.find({ type: 'Button', key: 'discard' })) confirms++
  }

  // Guardar: aplica sin confirmar y no cierra.
  await $.command.run(panel('barra'))
  let ui = await mount()
  await ui.press({ key: 'bar.mode' })
  await ui.press({ key: 'save' })
  await seen(ui)
  expect([confirms, eng.closed.length]).toEqual([0, 0])
  expect(eng.json('statusline').mode).toBe('simple')

  // Guardar y salir: aplica y cierra, sin confirmar.
  await ui.press({ key: 'bar.mode' })
  await ui.press({ key: 'save-exit' })
  await seen(ui)
  expect([confirms, eng.closed]).toEqual([0, [`${PANE_ID}:plugin`]])
  expect(eng.json('statusline').mode).toBe('normal')
  await ui.unmount()

  // Salir sin cambios: cierra directo.
  await $.command.run(panel('barra'))
  ui = await mount()
  await ui.press({ key: 'exit' })
  await seen(ui)
  expect([confirms, eng.closed.length]).toEqual([0, 2])
  await ui.unmount()

  // Salir con cambios: UNA confirmación; Descartar cierra sin volver a preguntar.
  await $.command.run(panel('barra'))
  ui = await mount()
  await ui.press({ key: 'bar.mode' })
  await ui.press({ key: 'exit' })
  await seen(ui)
  expect(confirms).toBe(1)
  await ui.press({ key: 'discard' })
  await seen(ui)
  expect([confirms, eng.closed.length]).toEqual([1, 3])
  expect(eng.json('statusline').mode).toBe('normal')
  await ui.unmount()

  // Volver cierra la confirmación sin cerrar el pane.
  await $.command.run(panel('barra'))
  ui = await mount()
  await ui.press({ key: 'bar.mode' })
  await ui.press({ key: 'exit' })
  await ui.press({ key: 'back' })
  expect(await ui.find({ type: 'Button', key: 'discard' })).toBeUndefined()
  expect(eng.closed.length).toBe(3)
  await ui.unmount()
})

test('/clear: una sola confirmación', async ($, on) => {
  const eng = engine(on)
  await $.command.run(panel('sesion'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'act-clear' })
  expect(await ui.findAll({ type: 'Button', key: 'clear-yes' })).toHaveLength(1)
  await ui.press({ key: 'clear-yes' })
  expect(await ui.find({ type: 'Button', key: 'clear-yes' })).toBeUndefined()
  expect(eng.ran).toEqual(['clear'])
  await ui.unmount()
})

test('filas con sangría de 2 y valores en una columna fija cerca de la etiqueta', async ($, on) => {
  engine(on)
  await $.command.run(panel())
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(60),
  })
  // Etiqueta más larga por pestaña (Barra: "Tema de Claude"; Sesión: "Avisos de caché y plan").
  for (const [tab, keys, longest] of [
    ['barra', ['bar.mode', 'bar.theme', 'bar.quiet', 'bar.cut', 'claude.theme'], 'Tema de Claude'.length],
    ['sesion', ['session.autocompact', 'notify.on', 'notify.ttl'], 'Avisos de caché y plan'.length],
  ] as const) {
    await ui.press({ key: `tab-${tab}` })
    const texts = await Promise.all(keys.map(async k => (await ui.find({ type: 'Button', key: k }))?.text ?? ''))
    for (const t of texts) {
      expect(t).toMatch(/^[▌ ] [^ ]/)
      expect(t.length).toBe(45)
      // Columna = sangría 2 + etiqueta más larga + 2, lejos del borde derecho.
      expect(t.indexOf('‹')).toBe(2 + longest + 2)
    }
  }
  // Los botones de acción van con la misma sangría que las filas.
  const indented = (await ui.findAll({ type: 'Box' })).filter(b => b.props.paddingLeft === 2)
  expect(indented.length).toBe(2)
  // La ayuda describe el elemento con foco (la primera fila, tras cambiar de pestaña).
  expect(await ui.find({ type: 'Text', text: /^Desde cuántos tokens se auto-compacta/ })).toBeDefined()
  await ui.unmount()
})

test('nada se sale del borde: cada línea entra en el ancho menos 1', async ($, on) => {
  engine(on, {}, { fiveHour: 6, resetsAt: '2026-10-31T18:20:00' })
  await $.command.run(panel())
  for (const cols of [60, 45, 30]) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(cols),
    })
    const max = cols - 1
    for (const tab of ['barra', 'modelo', 'modos', 'sesion', 'perfiles']) {
      await ui.press({ key: `tab-${tab}` })
      if (tab === 'sesion') await ui.press({ key: 'act-clear' }) // confirmación de /clear
      const over = [...(await ui.findAll({ type: 'Text' })), ...(await ui.findAll({ type: 'Button' }))]
        .filter(x => x.text.length > max)
        .map(x => `${tab}@${cols}: ${JSON.stringify(x.text)}`)
      expect(over).toEqual([])
      // Ninguna caja pide más ancho, y cada fila de pestañas entra (con sus huecos).
      const boxes = await ui.findAll({ type: 'Box' })
      expect(boxes.filter(b => typeof b.props.width === 'number' && Number(b.props.width) > max)).toEqual([])
      for (const b of boxes.filter(b => b.key?.startsWith('tabs-'))) {
        expect(b.text.length + (b.children?.length ?? 1) - 1).toBeLessThanOrEqual(max)
      }
      if (tab === 'sesion') await ui.press({ key: 'clear-no' })
    }
    await ui.unmount()
  }
})

test('la ayuda de un ajuste describe solo el valor elegido y cambia al ciclar', async ($, on) => {
  engine(on)
  await $.command.run(panel('barra'))
  for (const cols of [60, 45]) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(cols),
    })
    const max = cols - 1
    const hintOf = async () => {
      const row = await ui.find({ type: 'Box', key: 'hint-row' })
      const [name, desc] = (await ui.findAll({ type: 'Text' })).filter(t =>
        (row?.children ?? []).some(c => JSON.stringify(c) === JSON.stringify({ type: t.type, props: t.props, children: t.children })),
      )
      return { row, name, desc }
    }
    await ui.press({ key: 'tab-barra' }) // el foco va a Modo
    // Arranca en experto: solo su descripción, en una línea que entra a 45.
    let h = await hintOf()
    expect(h.row?.text).toBe('Experto · todo el detalle: costo y caché')
    expect(h.row?.text.length).toBeLessThanOrEqual(Math.min(43, max))
    expect(await ui.find({ type: 'Text', text: /semáforo|barras de contexto/ })).toBeUndefined()
    // Nombre en el acento, descripción en el gris secundario.
    expect(h.name?.props.color).toBe('#b48ead')
    expect(h.desc?.props.color).toBe('#d8dee9')
    // Al ciclar con ‹ › la ayuda sigue al valor.
    await ui.press({ key: 'bar.mode' }) // experto -> simple
    h = await hintOf()
    expect(h.row?.text).toBe('Simple · semáforo y una sola acción')
    expect(await ui.find({ type: 'Text', text: /todo el detalle/ })).toBeUndefined()
    await ui.press({ key: 'bar.mode' }) // simple -> normal
    expect((await hintOf()).row?.text).toBe('Normal · barras de contexto y plan')
    await ui.press({ key: 'bar.mode' }) // vuelve a experto
    await ui.unmount()
  }
})

// Ancho que ocupa un árbol dibujado (aprox. del terminal): Text = su texto;
// fila = suma de hijos + huecos; columna = el hijo más ancho; más márgenes.
function widthOf(n: unknown): number {
  if (typeof n === 'string') return n.length
  if (n === null || typeof n !== 'object') return 0
  const node = n as Node
  const pad = Number(node.props?.marginLeft ?? 0) + Number(node.props?.paddingLeft ?? 0)
  const kids = (node.children ?? []).map(widthOf)
  if (node.type === 'Text' || node.type === 'Button' || node.props?.flexDirection === 'row' || node.type === undefined) {
    const gap = node.type === 'Box' ? Number(node.props?.columnGap ?? 0) * Math.max(0, kids.filter(k => k > 0).length - 1) : 0
    return pad + kids.reduce((a, b) => a + b, 0) + gap
  }
  return pad + Math.max(0, ...kids)
}

test('pestañas en columna a la izquierda desde 58 columnas; en fila más angosto', async ($, on) => {
  engine(on)
  await $.command.run(panel())
  for (const cols of [60, 58, 57, 56, 55, 45]) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(cols),
    })
    const vertical = cols >= 58
    for (const tab of ['barra', 'modelo', 'modos', 'sesion', 'perfiles']) {
      await ui.press({ key: `tab-${tab}` })
      // Ninguna línea supera el ancho menos 1, con las dos columnas y el margen izquierdo sumados.
      const root = (await ui.drawn()) as unknown as Node
      expect(widthOf(root)).toBeLessThanOrEqual(cols - 1)
      // Margen de 1 línea arriba y 1 columna a la izquierda, en los dos layouts.
      expect(root.props?.marginTop).toBe(1)
      expect(root.props?.marginLeft).toBe(1)
      expect(await ui.find({ type: 'Box', key: 'cols' }) !== undefined).toBe(vertical)
      expect(await ui.find({ type: 'Box', key: 'tabs-0' }) !== undefined).toBe(!vertical)
      if (vertical) {
        // Una pestaña por línea; la activa con la marca en el acento, el resto en gris.
        const tabs = (await ui.findAll({ type: 'Button' })).filter(b => b.key?.startsWith('tab-'))
        expect(tabs.map(b => b.text.trim())).toEqual(
          (
            [
              ['barra', 'Barra'],
              ['modelo', 'Modelo'],
              ['modos', 'Modos 4D'],
              ['sesion', 'Sesión'],
              ['perfiles', 'Perfiles'],
            ] as const
          ).map(([id, l]) => (id === tab ? `▌ ${l}` : l)),
        )
        // El separador vertical llega justo hasta el final del contenido.
        const cols_ = (await ui.find({ type: 'Box', key: 'cols' })) as unknown as Node
        const [tabCol, sep, content] = (cols_.children ?? []) as Node[]
        // ...y sigue por la línea vacía de antes del pie, donde se une en ┴.
        expect(rowsOf(sep)).toBe(Math.max(rowsOf(tabCol), rowsOf(content)) + 1)
        expect(JSON.stringify(sep)).toMatch(/│/)
      }
      // El pie (estado, 3 botones, teclas) sigue debajo, a lo ancho.
      for (const key of ['save', 'save-exit', 'exit']) expect(await ui.find({ type: 'Button', key })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /Esc salir/ })).toBeDefined()
    }
    // Las ayudas de 43 caracteres o menos entran en una línea.
    await ui.press({ key: 'tab-barra' })
    expect((await ui.find({ type: 'Box', key: 'hint-row' }))?.text).toBe('Experto · todo el detalle: costo y caché')
    await ui.unmount()
  }
})

// Dibujo aproximado del terminal: una línea por Text/Button, filas lado a lado
// (rellenadas al ancho de cada hijo), columnas apiladas, márgenes y sangrías.
function draw(n: unknown): string[] {
  if (typeof n === 'string') return [n]
  if (!n || typeof n !== 'object') return []
  const node = n as Node
  const ml = ' '.repeat(Number(node.props?.marginLeft ?? 0) + Number(node.props?.paddingLeft ?? 0))
  const mt = Number(node.props?.marginTop ?? 0)
  const kids = (node.children ?? []).map(draw)
  let out: string[]
  if (node.type === 'Text' || node.type === 'Button') out = [kids.flat().join('')]
  else if (node.props?.flexDirection === 'row') {
    const h = Math.max(0, ...kids.map(k => k.length))
    const ws = kids.map(k => Math.max(0, ...k.map(x => x.length)))
    const gap = node.props?.justifyContent === 'space-between' ? '  ' : ' '.repeat(Number(node.props?.columnGap ?? 0))
    out = Array.from({ length: h }, (_, i) => kids.map((k, j) => (k[i] ?? '').padEnd(ws[j] ?? 0)).join(gap))
  } else out = kids.flat()
  return [...Array<string>(mt).fill(''), ...out.map(x => ml + x)]
}

test('ritmo vertical: pestaña y primer título en la misma fila, nunca dos líneas vacías seguidas', async ($, on) => {
  engine(on)
  await $.command.run(panel())
  for (const cols of [60, 45]) {
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(cols),
    })
    const vertical = cols >= 58
    for (const tab of ['barra', 'modelo', 'modos', 'sesion', 'perfiles']) {
      await ui.press({ key: `tab-${tab}` })
      const out = draw(await ui.drawn())
      // Margen izquierdo 1; en columna, el contenido empieza después de pestañas (11) + │ + 1.
      const contentOf = (l: string) => (vertical ? l.slice(14) : l.slice(1))
      // Un solo margen superior: la fila 0 vacía, la 1 con contenido.
      expect(out[0]?.trim()).toBe('')
      expect(contentOf(out[1] ?? '').trim()).not.toBe('')
      if (vertical) {
        // La primera pestaña y el primer título de sección, en la misma fila.
        expect(out[1]).toMatch(/^ [▌ ] Barra/)
        expect(contentOf(out[1] ?? '')).toMatch(/^[A-ZÁÉÍÓÚ]{3}/)
        // El separador vertical termina justo en la línea del pie y se une en ┴.
        const join = out.findIndex(l => l.includes('┴'))
        expect(join).toBeGreaterThan(1)
        expect(out[join]?.indexOf('┴')).toBe(12)
        expect(out[join - 1]?.charAt(12)).toBe('│')
        expect(out[join]?.trim().length).toBe(cols - 2)
      }
      // Nunca dos líneas vacías seguidas (en columna, vacía = sin contenido a la derecha).
      const blank = out.map((l, i) => i > 0 && contentOf(l).trim() === '' && !/[─┴]/.test(l))
      const doubles = blank.map((b, i) => b && blank[i + 1]).filter(Boolean)
      expect(doubles.length).toBe(0)
      // Pie: los atajos al mismo margen izquierdo que la línea del pie.
      const keys = out.findIndex(l => /Esc salir/.test(l))
      expect(out[keys]?.startsWith(' Tab') || out[keys]?.startsWith(' ↑↓') || out[keys]?.startsWith(' Enter')).toBe(true)
    }
    await ui.unmount()
  }
})

test('falla parcial: el borrador conserva lo que falló y Guardar y salir no cierra', async ($, on) => {
  const eng = engine(on, {}, { failCommand: 'autocompact' })
  await $.command.run(panel('sesion'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'notify.ttl' }) // 5 -> 60
  await ui.press({ key: 'session.autocompact' }) // sin dato -> 200000
  await ui.press({ key: 'save-exit' })

  expect(eng.json('panel4d')).toEqual({ cacheTtlMin: 60 })
  expect(eng.toasts.at(-1)).toMatch(/guardado a medias\. Falló: Auto-compact .*Quedó: TTL/)
  expect(eng.closed).toEqual([])
  // Solo queda pendiente lo que falló.
  expect(await ui.find({ type: 'Text', text: /1 cambio sin guardar|1 sin guardar/ })).toBeDefined()
  await ui.unmount()
})

test('Salir mientras se guarda no pide confirmación ni deja "0 cambios"', async ($, on) => {
  let release = () => {}
  const hold = new Promise<void>(r => (release = r))
  const eng = engine(on, {}, { holdCommand: hold })
  await $.command.run(panel('sesion'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'session.autocompact' })
  // Salir con el guardado en curso (antes o después de marcarse busy): al
  // terminar, sin pendientes, no queda la confirmación colgada.
  const saving = ui.press({ key: 'save' })
  await ui.press({ key: 'exit' })
  release()
  await saving
  expect(eng.ran).toEqual(['autocompact 200000'])
  expect(await ui.find({ type: 'Button', key: 'discard' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /0 cambios|0 sin guardar/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /Sin cambios/ })).toBeDefined()
  expect(eng.closed).toEqual([])
  await ui.unmount()
})

// Paridad con tests/fluency-4d/fixtures/flags_parity.json (los tests del panel no
// leen archivos reales: el fs es el del engine falso). Valor de cada fila del panel.
// Un caso por cada caso del fixture con adhd o caveman y sin verify, con el mismo
// nombre y contenido: tests/fluency-4d/test_panel_contract.py lo verifica.
const FLAG_CASES: {
  name: string
  adhd?: string
  caveman?: string
  expected: { adhd: string; caveman: string }
}[] = [
  {
    name: 'adhd auto',
    adhd: '{"on":true,"level":"auto"}',
    expected: { adhd: 'auto', caveman: 'off' },
  },
  {
    name: 'adhd lite',
    adhd: '{"on":true,"level":"lite"}',
    expected: { adhd: 'lite', caveman: 'off' },
  },
  {
    name: 'adhd full',
    adhd: '{"on":true,"level":"full"}',
    expected: { adhd: 'full', caveman: 'off' },
  },
  {
    name: 'adhd off',
    adhd: '{"on":false,"level":"full"}',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'adhd on como string no cuenta',
    adhd: '{"on":"true","level":"lite"}',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'adhd sin level',
    adhd: '{"on":true}',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'adhd level ultra (solo caveman lo tiene)',
    adhd: '{"on":true,"level":"ultra"}',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'adhd JSON corrupto',
    adhd: '{on: true',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'adhd JSON lista',
    adhd: '[true]',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'caveman auto',
    caveman: '{"on":true,"level":"auto"}',
    expected: { adhd: 'off', caveman: 'auto' },
  },
  {
    name: 'caveman ultra',
    caveman: '{"on":true,"level":"ultra"}',
    expected: { adhd: 'off', caveman: 'ultra' },
  },
  {
    name: 'caveman off',
    caveman: '{"on":false,"level":"lite"}',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'caveman level invalido',
    caveman: '{"on":true,"level":"max"}',
    expected: { adhd: 'off', caveman: 'off' },
  },
  {
    name: 'ambos activos: ADHD cede ante caveman',
    adhd: '{"on":true,"level":"full"}',
    caveman: '{"on":true,"level":"lite"}',
    expected: { adhd: 'off', caveman: 'lite' },
  },
  {
    name: 'caveman invalido no hace ceder a ADHD',
    adhd: '{"on":true,"level":"lite"}',
    caveman: '{"on":true,"level":"max"}',
    expected: { adhd: 'lite', caveman: 'off' },
  },
  {
    name: 'caveman off no hace ceder a ADHD',
    adhd: '{"on":true,"level":"auto"}',
    caveman: '{"on":false,"level":"full"}',
    expected: { adhd: 'auto', caveman: 'off' },
  },
]

test('paridad de flags: nivel inválido es off y ADHD cede ante caveman (como barra y hooks)', async ($, on) => {
  const eng = engine(on)
  for (const c of FLAG_CASES) {
    delete eng.files[`${DIR}/adhd.json`]
    delete eng.files[`${DIR}/caveman.json`]
    if (c.adhd !== undefined) eng.files[`${DIR}/adhd.json`] = c.adhd
    if (c.caveman !== undefined) eng.files[`${DIR}/caveman.json`] = c.caveman
    await $.command.run(panel('4d'))
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(),
    })
    const adhd = (await ui.find({ type: 'Button', key: 'mode.adhd' }))?.text ?? ''
    const caveman = (await ui.find({ type: 'Button', key: 'mode.caveman' }))?.text ?? ''
    expect(`${c.name}: ${adhd.match(/‹ (\S+) ›/)?.[1]}`).toBe(`${c.name}: ${c.expected.adhd}`)
    expect(`${c.name}: ${caveman.match(/‹ (\S+) ›/)?.[1]}`).toBe(`${c.name}: ${c.expected.caveman}`)
    await ui.press({ key: 'exit' })
    await ui.unmount()
  }
})

// ADHD prendido pero oculto por caveman: apagar caveman en el borrador lo muestra
// con su nivel real (al guardar vuelve a correr), y elegirlo off se escribe.
test('apagar caveman muestra el ADHD que tenía oculto, con su nivel real', async ($, on) => {
  const eng = engine(on)
  eng.files[`${DIR}/adhd.json`] = '{"on": true, "level": "full"}'
  await $.command.run(panel('4d'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  const row = async (key: string) =>
    ((await ui.find({ type: 'Button', key }))?.text ?? '').match(/‹ (\S+) ›/)?.[1]
  expect(await row('mode.adhd')).toBe('off')
  await ui.press({ key: 'mode.caveman' }) // ultra -> off
  expect(await row('mode.caveman')).toBe('off')
  expect(await row('mode.adhd')).toBe('full')
  // Volver a prender caveman lo oculta de nuevo, sin pendiente de ADHD.
  await ui.press({ key: 'mode.caveman' }) // off -> auto
  expect(await row('mode.adhd')).toBe('off')
  await ui.press({ key: 'mode.caveman' }) // auto -> lite
  await ui.press({ key: 'mode.caveman' }) // lite -> full
  await ui.press({ key: 'mode.caveman' }) // full -> ultra
  await ui.press({ key: 'mode.caveman' }) // ultra -> off
  expect(await row('mode.adhd')).toBe('full')
  // Elegir ADHD off con caveman off: queda pendiente y se escribe.
  await ui.press({ key: 'mode.adhd' }) // full -> off
  expect(await row('mode.adhd')).toBe('off')
  await ui.press({ key: 'save' })
  expect(eng.json('adhd')).toEqual({ on: false, level: 'full' })
  expect(eng.json('caveman')).toEqual({ on: false, level: 'ultra' })
  await ui.unmount()
})

test('apagar caveman con ADHD oculto y guardar deja ADHD activo, como mostraba el panel', async ($, on) => {
  const eng = engine(on)
  eng.files[`${DIR}/adhd.json`] = '{"on": true, "level": "lite"}'
  await $.command.run(panel('4d'))
  const ui = await $.ui.mount({
    plugin: PLUGIN,
    component: 'Pane',
    requestId: PANE_ID,
    surface: 'terminal',
    props: paneProps(),
  })
  await ui.press({ key: 'mode.caveman' }) // ultra -> off
  expect((await ui.find({ type: 'Button', key: 'mode.adhd' }))?.text).toMatch(/‹ lite ›/)
  await ui.press({ key: 'save' })
  expect(eng.json('adhd')).toEqual({ on: true, level: 'lite' })
  expect(eng.json('caveman')).toEqual({ on: false, level: 'ultra' })
  // Tras guardar, el panel sigue mostrando ADHD lite (ahora sin caveman).
  expect((await ui.find({ type: 'Button', key: 'mode.adhd' }))?.text).toMatch(/‹ lite ›/)
  await ui.unmount()
})

// os.homedir()/Path.home(): HOME en POSIX, USERPROFILE (y después HOME) en Windows.
const HOME_CASES: { name: string; env: Record<string, string> }[] = [
  { name: 'POSIX con ambas: HOME', env: { HOME: '/home/t', USERPROFILE: '/otro' } },
  { name: 'POSIX solo USERPROFILE: respaldo', env: { USERPROFILE: '/home/t' } },
  {
    name: 'Windows con ambas: USERPROFILE',
    env: { OS: 'Windows_NT', USERPROFILE: '/home/t', HOME: '/otro' },
  },
  { name: 'Windows solo HOME', env: { OS: 'Windows_NT', HOME: '/home/t' } },
]

for (const c of HOME_CASES) {
  test(`home del panel: ${c.name}`, async ($, on) => {
    const eng = engine(on, {}, { env: c.env })
    eng.files['/otro/.claude/fluency4d/statusline.json'] = '{"mode":"simple"}'
    await $.command.run(panel('barra'))
    const ui = await $.ui.mount({
      plugin: PLUGIN,
      component: 'Pane',
      requestId: PANE_ID,
      surface: 'terminal',
      props: paneProps(),
    })
    // El statusline.json de /home/t dice experto; el de /otro, simple.
    expect((await ui.find({ type: 'Button', key: 'bar.mode' }))?.text).toMatch(/‹ experto › *$/)
    await ui.unmount()
  })
}

// Recarga del mod: el atom `prefs` queda en el default (TTL 5 min) aunque
// panel4d.json diga 60, y session.start no se repite. El timer del aviso tiene
// que releer el archivo; si no, avisa en falso ~4 min después del último turno.
test('aviso de caché: tras recargar el mod usa el TTL real del archivo (60 min), no el default', async ($, on) => {
  const eng = engine(on)
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  // session.start con el archivo vacío deja el atom en el default (5 min)...
  await $.session.start({ cwd: HOME, surface: 'terminal', isInteractive: true })
  // ...y el TTL real aparece en el archivo sin que session.start se repita.
  eng.files[`${DIR}/panel4d.json`] = '{"notify":true,"cacheTtlMin":60}'
  await $.turn.complete({
    answer: 'ok',
    durationMs: 1,
    isAborted: false,
    turnId: 't1',
    reason: 'answer',
  } as never)
  const cacheToasts = () => eng.toasts.filter(t => /La caché vence/.test(t))

  await eng.clock.advance(4.5 * 60_000)
  expect(cacheToasts()).toEqual([])

  await eng.clock.advance(56 * 60_000 - 4.5 * 60_000)
  expect(cacheToasts().length).toBe(1)
  const mins = Number(/~(\d+) min/.exec(cacheToasts()[0] ?? '')?.[1])
  expect(mins).toBeGreaterThanOrEqual(1)
  expect(mins).toBeLessThanOrEqual(4)
})
