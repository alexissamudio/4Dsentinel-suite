---
description: "Instala el binario de codebase-memory-mcp (grafo de codebase) y REGISTRA el MCP con ruta absoluta verificada (claude mcp add --scope user). El plugin ya NO declara el MCP. Triggers on '/suite-setup', 'instalar codebase-memory', 'setup de la suite'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/skills/suite-setup/SKILL.md. NO editar a mano. -->

# /suite-setup - /suite-setup - instalar y registrar codebase-memory-mcp (OpenCode)

Wrapper del skill `suite-setup` de la suite 4Dsentinel. El cuerpo canonico del flujo vive en el `SKILL.md` de la suite (plugins/memory/skills/suite-setup/SKILL.md); este comando lo dispara en OpenCode.

Segui el flujo del skill al pie de la letra, adaptando las rutas y herramientas al entorno OpenCode (no hay hooks automaticos de Claude Code; usas las herramientas nativas de OpenCode).

## Degradacion cross-harness

- Los hooks de Claude Code (`UserPromptSubmit`, `PostToolUse`, `Stop`) NO corren en OpenCode; si la skill los asume, hace el trabajo equivalente a mano.
- Las referencias a `~/.claude/` se traducen a las rutas equivalentes de OpenCode (`~/.config/opencode/`).
- Las invocaciones a `sentinel-agents:*` se mantienen igual (los subagentes de OpenCode replican el contrato).

Argumentos opcionales: `$ARGUMENTS`.
