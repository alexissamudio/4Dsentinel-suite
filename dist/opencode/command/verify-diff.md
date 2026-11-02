---
description: "Activa o desactiva el gate de verificación del diff de fluency-4d: al cerrar una tarea, bloquea UNA vez por sesión recordando verificar el diff (con /sentinel-audit tipo=review si tenés sentinel-agents, o revisando vos el git diff). Es opt-in: arranca apagado. Triggers on: '/verify-diff', 'verificar el diff', 'gate de diligencia', 'verify diff off', 'apagar verify'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/verify-diff/SKILL.md. NO editar a mano. -->

# /verify-diff - /verify-diff — Toggle del gate "verificá el diff" (OpenCode)

Wrapper del skill `verify-diff` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/fluency-4d/skills/verify-diff/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
