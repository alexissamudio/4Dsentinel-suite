---
name: statusline
description: "Instala, quita o revisa la barra de estado de fluency-4d (y el atajo del Panel 4D): setup copia el script a ~/.claude/fluency4d/ y configura statusLine con backup y sin pisar lo ajeno; remove revierte exactamente lo que agregó; status muestra qué está instalado y si hay que re-sincronizar. Requiere Node.js. Solo Claude Code. Triggers on: '/statusline', '/statusline setup', '/statusline remove', '/statusline status', 'instalar la barra de estado', 'quitar la barra'."
argument-hint: "[setup|remove|status]"
allowed-tools: Bash(uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/statusline_setup.py" setup) Bash(uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/statusline_setup.py" setup --keybinding) Bash(uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/statusline_setup.py" setup --copy-theme) Bash(uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/statusline_setup.py" setup --keybinding --copy-theme) Bash(uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/statusline_setup.py" remove) Bash(uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/statusline_setup.py" status)
---

# /statusline — Instalar, quitar o revisar la barra de estado

Toda la lógica vive en un script Python testeado; este skill solo elige el
subcomando, explica y pide confirmación. NUNCA edites `settings.json` ni
`keybindings.json` a mano desde acá.

El script es:

```bash
uv run --script "${CLAUDE_PLUGIN_ROOT}/hooks/statusline_setup.py" <sub> [flags]
```

Escribí el comando EXACTAMENTE así (comillas dobles incluidas, sin opciones extra
de `uv` ni otra ruta): `allowed-tools` aprueba solo esa forma, con la ruta del plugin
ya expandida por Claude Code y los subcomandos de la lista. Cualquier otra variante
(otra ruta, una URL, `--with`, `--force`) le pide permiso al usuario, a propósito.

Si `${CLAUDE_PLUGIN_ROOT}` llegara sin expandir, usá la carpeta base de este skill
(la que muestra Claude Code al cargarlo) y subí dos niveles:
`<base>/../../hooks/statusline_setup.py`. En ese caso Claude Code pide permiso para
cada ejecución: es lo esperado, no lo esquives.

## 1. Parseá el argumento

Resolvé UN subcomando de la lista cerrada: `setup`, `remove`, `status`.
Sin argumento o con otra cosa → `status`. NUNCA pases texto libre del usuario.

## 2. `setup`

Antes de correrlo, explicá en pocas líneas qué va a tocar:

- Copia el script de la barra a `~/.claude/fluency4d/statusline.js` (ruta fija).
- Antes de cambiar `~/.claude/settings.json` o `keybindings.json` hace backup
  fechado en `~/.claude/fluency4d/backups/` (quedan los 3 más recientes) y, la
  primera vez, un `<archivo>.orig.bak` fijo que la poda nunca borra. Si encuentra
  un `.orig.bak` de una instalación anterior, lo renombra a `<archivo>.orig.<fecha>.bak`
  y lo conserva siempre.
- Si `CLAUDE_CONFIG_DIR` está definido, `settings.json`, `keybindings.json` y
  `themes/` se toman de esa carpeta; la copia, `setup.json` y los backups siguen en
  `~/.claude/fluency4d/`.
- Agrega `statusLine` apuntando a esa copia, solo si no hay otro.
- Si `env.CLAUDE_CODE_PLUGIN_DIRS` apunta a un mod `panel-4d` local, lo quita para
  que `/panel` no quede registrado dos veces (remove lo restaura).
- Todo queda anotado en `~/.claude/fluency4d/setup.json` ANTES de escribir; si un
  paso falla, revierte lo ya escrito y sale con 1.

Opcionales (preguntá si los quiere, no los actives solos):

- `--keybinding`: atajo `ctrl+x ctrl+p` → `/panel` (solo si la tecla
  está libre; si ya apunta a `/panel`, avisa "ya estaba configurado" y no la
  toca). Experimental: avisá que todavía no se probó en vivo.
- `--copy-theme`: copia el tema Templado a `~/.claude/themes/`. Normalmente no
  hace falta porque el plugin ya lo trae.

Corré `setup` con los flags elegidos, en este orden: `setup [--keybinding] [--copy-theme]`
(es el orden que habilita `allowed-tools`; `--force` NO está habilitado a propósito, así
que Claude Code le pide permiso al usuario). Leé el código de salida:

- **0**: listo. Decí que **reinicie Claude Code**, que el tema se elige con
  `/theme` (Templado) y que el panel se abre con `/panel` (o con `ctrl+x ctrl+p`
  si se configuró el atajo). El modo de la barra se cambia con `/barra`. La barra
  se refresca cada 5 s (`refreshInterval`) y además con cada mensaje.
- **2**: ya hay un `statusLine` que no es el de fluency-4d. Mostrale el valor que
  imprimió el script y PREGUNTÁ si quiere reemplazarlo. Solo con un sí explícito,
  repetí con `--force` (el valor previo queda guardado y `remove` lo restaura).
- **1**: mostrá el error tal cual. Si falta Node, decí que lo instale (LTS desde
  nodejs.org), abra una terminal nueva y reintente. Si `settings.json` no es JSON
  válido, el script no tocó nada: el usuario tiene que arreglarlo primero.

## 3. `remove`

Corré `remove` sin flags. Revierte solo lo que registró el setup: restaura el
`statusLine` previo (o lo borra si no había), restaura `CLAUDE_CODE_PLUGIN_DIRS`,
quita el atajo si sigue siendo el nuestro y borra la copia fija y el tema copiado.
Si el resultado equivale al original, lo deja byte a byte como estaba. Los backups
fechados quedan; se borran solo los `.orig.bak` que creó esta instalación, y solo si
todo se restauró sin avisos. Si el `statusLine` cambió desde el setup, no se toca y
la copia fija tampoco se borra (puede que tu comando la siga llamando). Confirmá en
1-2 líneas y pedí reiniciar Claude Code.

## 4. `status`

Corré `status` y resumí en pocas líneas: Node, copia fija (sincronizada o no),
`statusLine`, atajo y tema. Si aparece `SUGERENCIA`, ofrecé correr
`/statusline setup` para re-sincronizar la copia fija con la versión del plugin.

## Reglas

- NUNCA uses `--force` sin el sí explícito del usuario a reemplazar su `statusLine`.
- NUNCA edites a mano los JSON del usuario; si el script falla, reportá el error.
- La barra y el panel son solo de Claude Code (no existen en Codex ni OpenCode).
