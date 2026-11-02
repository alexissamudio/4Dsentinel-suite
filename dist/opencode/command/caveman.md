---
description: "Activa o desactiva el modo Caveman de fluency-4d: un estilo de comunicación token-eficiente ('why use many token when few token do trick') que recorta el relleno de las respuestas SIN tocar código, comandos ni mensajes de error. Es opt-in: arranca apagado. Triggers on: '/caveman', 'modo caveman', 'talk like caveman', 'modo normal', 'normal mode'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/caveman/SKILL.md. NO editar a mano. -->

# /caveman - /caveman — Toggle del modo de comunicación token-eficiente (OpenCode)

Wrapper del skill `caveman` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/fluency-4d/skills/caveman/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
