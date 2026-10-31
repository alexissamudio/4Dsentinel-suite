// Lo que el panel sabe de la sesión en vivo (para el resumen y los toasts).
export type Panel4dLive = {
  effort?: string
  model?: string
  fast?: string
  tokens?: number
  window?: number
  percent?: number
  fiveHour?: number
  fiveHourResetsAt?: string
  lastTurnAt?: number
  autoCompact?: string
}

// Preferencias propias del panel (espejo de ~/.claude/fluency4d/panel4d.json).
export type Panel4dPrefs = { notify: boolean; cacheTtlMin: number }

export type Panel4dTab = 'barra' | 'modelo' | 'modos' | 'sesion' | 'perfiles'

// Estado del pane: pestaña, borrador (lo editado y no guardado) y valores reales.
export type Panel4dUi = {
  tab: Panel4dTab
  // id de ajuste -> valor elegido; solo lo que difiere de `current`.
  draft: Record<string, string>
  // id de ajuste -> valor real (archivos, settings, sesión) al abrir o guardar.
  current: Record<string, string>
  // Opciones válidas del tema de Claude, tal como las lista /config.
  themeOptions: string[]
  // Etiqueta de cada opción que no se muestra tal cual (temas custom: su `name`).
  themeNames?: Record<string, string>
  // Tema de la barra (statusline.json) con el que se pinta el pane; sin él, el de Claude.
  paneTheme?: string
  // Fila de confirmación abierta: salir con pendientes, o /clear.
  confirm?: 'exit' | 'clear'
  // Elemento con el foco (para la ayuda contextual).
  focus?: string
  busy?: boolean
  // Cierre ya decidido (Guardar y salir, Descartar y salir, Salir sin cambios):
  // el hook de ui.close no vuelve a preguntar.
  closing?: boolean
  note?: string
}

declare module 'claude-code' {
  interface PluginState {
    'fluency-4d': {
      live: Shaped<Panel4dLive>
      prefs: Shaped<Panel4dPrefs>
      ui: Shaped<Panel4dUi>
    }
  }
}
