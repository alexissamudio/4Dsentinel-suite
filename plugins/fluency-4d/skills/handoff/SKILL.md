---
name: handoff
description: "Genera el handoff de cierre de sesion para cortar y arrancar limpio: recolecta git (rama, commits, cambios), el plan activo y el estado previo, actualiza .claude/docs/estado-sesion.md con rutas/hecho/pendiente, sugiere el commit (no lo ejecuta), respeta persistencia (borra el estado si no quedan pendientes) y copia un resumen al portapapeles para pegar en la sesion nueva. Es la contraparte de escritura de /4d-status. Triggers on: '/handoff'."
---

# /handoff — Checkpoint de cierre de sesion

Cortar la sesion cuando el contexto se llena o cambia el foco es la palanca #1 de
higiene de tokens. Este comando arma el handoff de forma **dinamica** (nada
hardcodeado): junta el estado real y deja todo listo para arrancar una sesion nueva.
Es READ-ONLY salvo que escribe el propio `estado-sesion.md` (y quiza borra el viejo).

## 1. Recolecta el contexto (dinamico)

En el cwd, corre y anota (no inventes, leelo del sistema):
- Rama actual y remote: `git branch --show-current`, `git remote get-url origin`.
- Commits de la sesion: `git log <base>..HEAD --oneline` con `base` = `origin/main`
  o el merge-base (`git merge-base HEAD origin/main`). Si no hay git, decilo y segui.
- Cambios sin commitear: `git status --porcelain`.
- Plan activo: el `.md` mas reciente en `~/.claude/plans/` (por mtime), o el de la tarea.
- Handoff previo: lee `.claude/docs/estado-sesion.md` y `.claude/docs/lecciones.md`.

## 2. Arma las rutas del proyecto

Una tabla corta: cwd, repo/remote, rama, plan activo, y los docs clave del proyecto
(p. ej. bridges e informes bajo `.claude/docs/`). Rutas reales, detectadas, no de ejemplo.

## 3. Escribi/actualiza `.claude/docs/estado-sesion.md`

Este es el handoff persistente. Esquema (es un **superset** del que inyecta el hook de
checkpoint: fecha, objetivo/frase 4D, decisiones, pendientes — no lo contradigas, lo amplias):
- `# Estado de sesion — <fecha> — <estado en una linea>`
- `## Objetivo / frase 4D` — la dimension 4D y la meta.
- `## Hecho` — commits `hash + subject` y entregables verificados.
- `## Pendiente` — lo que queda, con referencias `archivo:linea`.
- `## Rutas` — la tabla del paso 2.
- `## Proximo paso` — la primera accion de la sesion nueva.

## 4. Consolida `lecciones.md`

Si hubo correcciones del usuario o errores cazados, agregalos a `.claude/docs/lecciones.md`
(acumula, fusiona duplicadas, max ~30). Ver el criterio en `persistencia.md` (flow-forward).

## 5. Sugeri el commit (opt-in, NO ejecutes)

Si hay cambios sin commitear o commits sin pushear, **mostra** el comando exacto sugerido
(commit convencional, subject <= 50 chars, sin atribucion de IA; push; PR si aplica). El
humano confirma y lo corre. Nunca commitees ni pushees por tu cuenta.

## 6. Aplica persistencia

Segun `persistencia.md`: `estado-sesion.md` es living **mientras hay pendientes**; si la
tarea cerro **sin** pendientes, ofrece BORRARLO (un estado residual miente). Con pendientes,
queda actualizado.

## 7. Emiti el handoff y copialo al portapapeles

Genera un bloque conciso listo para pegar en la sesion nueva: rutas + estado + hecho +
por hacer + proximo paso. Escribilo a un archivo temporal (en el scratchpad de sesion, no
en el repo) y copialo al portapapeles con la utilidad de la plataforma; ademas mostralo en
el chat. Deteccion de SO con fallback (si no hay utilidad, avisa y deja el bloque en el chat):
- Windows: `cat <tmp> | clip`
- macOS: `cat <tmp> | pbcopy`
- Linux: `wl-copy < <tmp>` (Wayland) o `xclip -selection clipboard < <tmp>`

Confirma al usuario: handoff escrito, commit sugerido (si aplica) y "copiado al portapapeles".

## Formato

Menos de ~30 lineas de salida en el chat. Sin relleno: es un handoff, no un ensayo.
