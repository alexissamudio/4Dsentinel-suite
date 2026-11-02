---
description: "Activa o desactiva el modo ADHD/TDAH de fluency-4d: un estilo de comunicación accionable y estructurado (arranca por la acción, pasos numerados, next-step concreto) que ayuda a mantener el foco SIN tocar código, comandos ni mensajes de error. Es opt-in: arranca apagado. Triggers on: '/adhd', 'modo adhd', 'modo tdah', 'stop adhd mode', '/adhd off'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/adhd/SKILL.md. NO editar a mano. -->

# /adhd - /adhd — Toggle del modo de comunicación accionable y estructurada (OpenCode)

Wrapper del skill `adhd` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/fluency-4d/skills/adhd/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
