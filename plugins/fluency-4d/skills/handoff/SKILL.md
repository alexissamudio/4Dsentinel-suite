---
name: handoff
description: "Genera el handoff de cierre de sesión para cortar y arrancar limpio: recolecta git (rama, commits, cambios), el plan activo y el estado previo, actualiza .claude/docs/estado-sesion.md con rutas/hecho/pendiente, sugiere el commit (no lo ejecuta), respeta persistencia (borra el estado si no quedan pendientes) y copia un resumen al portapapeles para pegar en la sesión nueva. Es la contraparte de escritura de /4d-status. Triggers on: '/handoff'."
---

# /handoff — Checkpoint de cierre de sesión

Cortar la sesión cuando el contexto se llena o cambia el foco es la palanca #1 de
higiene de tokens. Este comando arma el handoff de forma **dinámica** (nada
hardcodeado): junta el estado real y deja todo listo para arrancar una sesión nueva.
Es READ-ONLY salvo que escribe el propio `estado-sesion.md` (y quizá borra el viejo).

## 1. Recolectá el contexto (dinámico)

En el cwd, corré y anotá (no inventes, leélo del sistema):
- Rama actual y remote: `git branch --show-current`, `git remote get-url origin`.
- Commits de la sesión: `git log <base>..HEAD --oneline` con `base` = `origin/main`
  o el merge-base (`git merge-base HEAD origin/main`). Si no hay git, decilo y seguí.
- Cambios sin commitear: `git status --porcelain`.
- Plan activo: el `.md` más reciente en `~/.claude/plans/` (por mtime), o el de la tarea.
- Handoff previo: leé `.claude/docs/estado-sesion.md` y `.claude/docs/lecciones.md`.

## 2. Armá las rutas del proyecto

Una tabla corta: cwd, repo/remote, rama, plan activo, y los docs clave del proyecto
(p. ej. bridges e informes bajo `.claude/docs/`). Rutas reales, detectadas, no de ejemplo.

## 3. Escribí/actualizá `.claude/docs/estado-sesion.md`

Este es el handoff persistente. Esquema (es un **superset** del que inyecta el hook de
checkpoint: fecha, objetivo/frase 4D, decisiones, pendientes — no lo contradigas, lo ampliás):
- `# Estado de sesión — <fecha> — <estado en una línea>`
- `## Objetivo / frase 4D` — la dimensión 4D y la meta.
- `## Hecho` — commits `hash + subject` y entregables verificados.
- `## Pendiente` — lo que queda, con referencias `archivo:línea`.
- `## Rutas` — la tabla del paso 2.
- `## Próximo paso` — la primera acción de la sesión nueva.

## 4. Consolidá `lecciones.md`

Si hubo correcciones del usuario o errores cazados, agregalos a `.claude/docs/lecciones.md`
(acumulá, fusioná duplicadas, máx ~30). Ver el criterio en `persistencia.md` (flow-forward).

## 5. Sugerí el commit (opt-in, NO ejecutes)

Si hay cambios sin commitear o commits sin pushear, **mostrá** el comando exacto sugerido
(commit convencional, subject <= 50 chars, sin atribución de IA; push; PR si aplica). El
humano confirma y lo corre. Nunca commitees ni pushees por tu cuenta.

## 6. Aplicá persistencia

Según `persistencia.md`: `estado-sesion.md` es living **mientras hay pendientes**; si la
tarea cerró **sin** pendientes, ofrecé BORRARLO (un estado residual miente). Con pendientes,
queda actualizado.

## 7. Emití el handoff y copialo al portapapeles

Generá un bloque conciso listo para pegar en la sesión nueva: rutas + estado + hecho +
por hacer + próximo paso. Escribilo a un archivo temporal (en el scratchpad de sesión, no
en el repo) y copialo al portapapeles con la utilidad de la plataforma; además mostralo en
el chat. Detección de SO con fallback (si no hay utilidad, avisá y dejá el bloque en el chat):
- Windows (PowerShell): `Get-Content -Raw -Encoding UTF8 <tmp> | Set-Clipboard` (NO `cat <tmp> | clip`: `clip.exe` decodifica stdin con la codepage OEM y rompe los acentos UTF-8 → mojibake)
- macOS: `cat <tmp> | pbcopy`
- Linux: `wl-copy < <tmp>` (Wayland) o `xclip -selection clipboard < <tmp>`

Confirmá al usuario: handoff escrito, commit sugerido (si aplica) y "copiado al portapapeles".

## Formato

Menos de ~30 líneas de salida en el chat. Sin relleno: es un handoff, no un ensayo.
