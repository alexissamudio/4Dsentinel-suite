---
description: "Muestra el estado del sistema fluency-4d en el proyecto actual: temas puenteados, lecciones, estado de sesión y sugerencias. Solo lectura. Triggers on: '/4d-status'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/4d-status/SKILL.md. NO editar a mano. -->

# /4d-status - /4d-status — Estado del sistema de puentes y aprendizaje (OpenCode)

Wrapper del skill `4d-status` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/fluency-4d/skills/4d-status/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
