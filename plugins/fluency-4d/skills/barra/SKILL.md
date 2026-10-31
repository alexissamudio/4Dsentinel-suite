---
name: barra
description: "Cambia el modo de la barra de estado de fluency-4d (simple | normal | experto), silencia o reactiva sus avisos (silencio | avisos) o cambia su tema (templado | tokyo-night | catppuccin | nord | gruvbox). Requiere la barra instalada con /statusline setup. Triggers on: '/barra', '/barra experto', '/barra silencio', 'modo de la barra'."
argument-hint: "[simple|normal|experto|silencio|avisos|templado|tokyo-night|catppuccin|nord|gruvbox]"
allowed-tools:
  - 'Bash(test -f "$HOME/.claude/fluency4d/statusline.js")'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode simple)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode normal)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode experto)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode silencio)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode avisos)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode templado)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode tokyo-night)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode catppuccin)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode nord)'
  - 'Bash(node "$HOME/.claude/fluency4d/statusline.js" mode gruvbox)'
---

# /barra — Modo, avisos y tema de la barra de estado

Este skill SOLO cambia la preferencia de la barra: el script de la status line
escribe `~/.claude/fluency4d/statusline.json` y la barra lo relee en cada render
(no hace falta reiniciar). Siempre se usa la **copia fija** instalada por
`/statusline setup`, nunca el script dentro del plugin.

## 1. Parseá el argumento

Del texto del usuario, resolvé UNA opción de esta lista cerrada:

- Modo: `simple`, `normal`, `experto`.
- Avisos: `silencio`, `avisos`.
- Tema: `templado`, `tokyo-night`, `catppuccin`, `nord`, `gruvbox`.

Sin argumento, o con algo fuera de la lista → no pases nada (el script muestra el
estado actual y el uso). NUNCA pases texto libre del usuario al comando.

## 2. Verificá la copia fija

La ruta es `<home>/.claude/fluency4d/statusline.js`, con el home del usuario
resuelto (en Bash: `$HOME`). Comprobá que exista:

```bash
test -f "$HOME/.claude/fluency4d/statusline.js"
```

Si NO existe: decí en 1 línea que la barra no está instalada y que corra
`/statusline setup`. No sigas.

## 3. Ejecutá

```bash
node "$HOME/.claude/fluency4d/statusline.js" mode <opcion>
```

(sin `<opcion>` si en el paso 1 no hubo una válida).

Escribí los comandos de los pasos 2 y 3 EXACTAMENTE así: una línea, `$HOME` sin
expandir, comillas dobles en la ruta, un espacio entre palabras y nada antes ni
después (sin `cd`, `&&`, pipes ni redirecciones). `allowed-tools` aprueba solo
esas formas, una por opción de la lista cerrada; cualquier otra pide permiso.

## 4. Confirmá

- Si la salida dice "Status line en modo ...": confirmá en UNA línea corta el
  modo, el estado de avisos y el tema activos, sin explicar nada más.
- Si dice "Uso:" (sin opción o inválida): mostrá el modo actual y las opciones:
  simple (semáforo y una acción), normal (barras con palabras), experto (todos
  los números); silencio (oculta consejos y etiquetas de aviso, los números siguen) y
  avisos (los vuelve a mostrar); temas: templado (grises, color solo para el
  estado), tokyo-night (default), catppuccin, nord, gruvbox.

## Reglas

- Solo la copia fija `~/.claude/fluency4d/statusline.js`; nunca una ruta del plugin
  ni una ruta de usuario escrita a mano.
- Solo opciones de la lista cerrada como argumento.
- Si falta la copia fija, la respuesta es `/statusline setup`, no instalarla a mano.
