---
description: "Genera el handoff de cierre de sesión para cortar y arrancar limpio: recolecta git (rama, commits, cambios), el plan activo y el estado previo, actualiza .claude/docs/estado-sesion.md con rutas/hecho/pendiente, sugiere el commit (no lo ejecuta), respeta persistencia (borra el estado si no quedan pendientes) y copia un resumen al portapapeles para pegar en la sesión nueva. Es la contraparte de escritura de /4d-status. Triggers on: '/handoff'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/handoff/SKILL.md. NO editar a mano. -->

# /handoff - checkpoint de cierre de sesion (OpenCode)

Wrapper del skill `handoff` de fluency-4d. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite; este comando lo dispara en OpenCode.

Segui el flujo `handoff` al pie de la letra:

1. Recolecta el contexto real de git (rama, ultimos commits, `git status`, diff) y el plan/estado de sesion previo.
2. Actualiza `.claude/docs/estado-sesion.md` (o el equivalente del proyecto) con rutas, lo hecho y lo pendiente.
3. Sugeri el mensaje de commit -- **NO** lo ejecutes.
4. Si no quedan pendientes, borra el estado viejo (persistencia).
5. Copia el resumen del handoff al portapapeles para pegar en la sesion nueva.

Argumentos opcionales: `$ARGUMENTS` (nota libre para el handoff).

NOTA (OpenCode): el paso del "plan activo" degrada a "sin plan" si el proyecto no tiene un directorio de planes -- el resto del flujo es cross-harness.

TODO(PoC): portar el resto de los skills de fluency-4d (`4d`, `4d-init`, `4d-status`, `4d-quiz`, `caveman`) como comandos OpenCode -- mismo patron de wrapper.
