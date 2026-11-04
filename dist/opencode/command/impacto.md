---
description: "Mapea los cambios de git a los simbolos afectados (envuelve detect_changes). Util antes de review o release."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/commands/impacto.md (cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->

# /impacto

Argumentos (`$ARGUMENTS`): [rango git opcional; por defecto los cambios sin commitear]

## Instrucciones

Mapeá los **cambios de git a los símbolos** (funciones/clases) afectados.

- **Proyecto:** resolvelo del repo actual si no se da.
- Llamá `detect_changes` (usá `$ARGUMENTS` como rango git si se da; si no, los cambios actuales
  sin commitear).
- Presentá en español: qué símbolos toca el diff y, si aporta, qué otros dependen de ellos (la
  **superficie de impacto**). Ideal antes de una code-review o un release.

## NOTA (OpenCode / MCP)

Este comando envuelve tools del MCP `codebase-memory`. En OpenCode se exponen con el prefijo del server (p. ej. `codebase-memory-mcp_search_graph` si el server se llama `codebase-memory-mcp` en `opencode.json`). Si el MCP no esta conectado, corre `/suite-setup` primero.
