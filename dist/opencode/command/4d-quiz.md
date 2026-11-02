---
description: "Quiz de opción múltiple para practicar la certificación AI Fluency (Anthropic Academy): 24 preguntas del marco 4D con corrección explicada y detección de temas débiles. Triggers on: '/4d-quiz', 'quiz 4d', 'practicar examen ai fluency'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/4d-quiz/SKILL.md. NO editar a mano. -->

# /4d-quiz - /4d-quiz — Práctica para la certificación AI Fluency (OpenCode)

Wrapper del skill `4d-quiz` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/fluency-4d/skills/4d-quiz/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
