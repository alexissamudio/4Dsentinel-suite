---
description: "Genera un CLAUDE.md modular con 'puentes' a documentación por tema: analiza el proyecto, crea .claude/docs/<tema>.md (auth, endpoints, database...) más bridges.json, y enlaza todo desde una tabla en CLAUDE.md sin pisar el contenido existente. Triggers on: '/4d-init', 'generar puentes', 'claude.md modular', 'puentes de documentacion'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/4d-init/SKILL.md. NO editar a mano. -->

# /4d-init - /4d-init — Generador de CLAUDE.md con puentes por tema (OpenCode)

Wrapper del skill `4d-init` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/fluency-4d/skills/4d-init/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
