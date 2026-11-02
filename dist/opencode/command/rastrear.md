---
description: "Rastrea llamadores/llamados e impacto de una funcion en el grafo (envuelve trace_path)."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/commands/rastrear.md (cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->

# /rastrear

Argumentos (`$ARGUMENTS`): <nombre de la funcion> [inbound|outbound|both]

## Instrucciones

Rastreá el **grafo de llamadas** de una función (análisis de impacto).

- **Proyecto:** resolvelo del repo actual si no se da.
- De `$ARGUMENTS`: el primer token es la función; si incluye `inbound`/`outbound`/`both`, usalo
  como `direction` (por defecto **`inbound`** = quién la llama = superficie de impacto).
- Llamá `trace_path` con `function_name=<función>`, `direction=<dir>`, `depth=2`.
- Presentá en español: llamadores/llamados agrupados por archivo/componente, y una lectura del
  **impacto** (dónde repercutiría un cambio a esa función).

## NOTA (OpenCode / MCP)

Este comando envuelve tools del MCP `codebase-memory`. En OpenCode se exponen con el prefijo del server (p. ej. `codebase-memory-mcp_search_graph` si el server se llama `codebase-memory-mcp` en `opencode.json`). Si el MCP no esta conectado, corre `/suite-setup` primero.
