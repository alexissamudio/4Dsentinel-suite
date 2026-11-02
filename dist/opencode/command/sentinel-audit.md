---
description: "Orquesta una auditoría encadenando los agentes de sentinel-agents (security, compliance ISO, code-review, validate) con handoff real entre ellos y un informe combinado. Usar cuando el usuario quiere auditar un proyecto/directorio de punta a punta. Triggers on: '/sentinel-audit', 'auditar con sentinel', 'auditoria completa'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/sentinel-agents/skills/sentinel-audit/SKILL.md. NO editar a mano. -->

# /sentinel-audit - /sentinel-audit — Orquestador de auditoría (OpenCode)

Wrapper del skill `sentinel-audit` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/sentinel-agents/skills/sentinel-audit/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
