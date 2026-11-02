---
name: memory-rastrear
description: Use when rastrear, trace. Trace function call graph via MCP.
version: 0.6.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [memory, codebase-memory, mcp, trace, call-graph]
    related_skills: [memory-buscar, memory-arquitectura]
---

# /rastrear — Rastrear grafo de llamadas (MCP codebase-memory)

Rastrea el grafo de llamadas de una funcion (analisis de impacto).

**Requiere:** MCP `codebase-memory` y repo indexado.

## Uso

`/rastrear <funcion> [inbound|outbound|both]`

- inbound (default): quien la llama → superficie de impacto
- outbound: a quien llama
- both: ambas

## Metodo

1. Llama `mcp_codebase_memory_trace_path` con `function_name=<f>`, `direction=<dir>`, `depth=2`.
2. Presenta: llamadores/llamados agrupados por archivo, lectura del impacto.
