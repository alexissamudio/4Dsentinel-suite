---
name: fluency-handoff
description: "Use when cerrar, checkpoint, sesion. Session handoff: state, commit, clipboard."
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, handoff, checkpoint, session, context]
    related_skills: [fluency-4d, fluency-4d-status]
---

# /handoff — Checkpoint de cierre de sesión

Cortar la sesión cuando el contexto se llena o cambia el foco es la palanca #1 de
higiene de tokens. Este comando arma el handoff de forma **dinámica** (nada
hardcodeado): junta el estado real y deja todo listo para arrancar una sesión nueva.

## 1. Recolectá el contexto

En el cwd, corré y anotá (no inventes):
- Rama y remote: `git branch --show-current`, `git remote get-url origin`.
- Commits: `git log <base>..HEAD --oneline`.
- Cambios sin commitear: `git status --porcelain`.
- Plan activo: el `.md` más reciente en `.hermes/plans/` (por mtime).
- Estado previo: leé `.hermes/docs/estado-sesion.md`.

## 2. Armá las rutas del proyecto

Tabla corta: cwd, repo/remote, rama, plan activo, docs clave.

## 3. Escribí `.hermes/docs/estado-sesion.md`

Esquema:
- `# Estado de sesión — <fecha>`
- `## Objetivo / frase 4D`
- `## Hecho` — commits y entregables verificados
- `## Pendiente` — con referencias `archivo:línea`
- `## Rutas` — tabla del paso 2
- `## Próximo paso`

## 4. Guardá lecciones

Si hubo correcciones del usuario o errores, guardalas con `memory` tool.

## 5. Sugerí el commit (opt-in, NO ejecutes)

Si hay cambios sin commitear, mostrá el comando sugerido (convencional, ≤50 chars).
El humano confirma y corre. Nunca commitees por tu cuenta.

## 6. Aplicá persistencia

Si la tarea cerró SIN pendientes, ofrecé borrar `estado-sesion.md`.
Con pendientes, queda actualizado.

## 7. Copiá al portapapeles

Generá un bloque conciso (rutas + estado + hecho + pendiente + próximo paso).
Copialo al portapapeles:
- Windows: `Get-Content -Raw -Encoding UTF8 <tmp> | Set-Clipboard`
- macOS: `cat <tmp> | pbcopy`
- Linux: `wl-copy < <tmp>` o `xclip -selection clipboard < <tmp>`

## Nota Hermes

Portado de Claude Code. Usa `.hermes/` en vez de `.claude/`. El portapapeles es
independiente de `pbcopy`/`clip` — usá la herramienta de la plataforma.
