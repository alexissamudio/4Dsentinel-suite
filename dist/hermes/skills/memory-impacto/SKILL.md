---
name: memory-impacto
description: Use when impacto, cambios. Map git changes to affected symbols via MCP.
version: 0.6.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [memory, codebase-memory, mcp, impact, git]
    related_skills: [memory-buscar, sentinel-code-reviewer]
---

# /impacto — Impacto de cambios (MCP codebase-memory)

Mapea cambios de git a simbolos afectados en el grafo. Ideal antes de review.

**Requiere:** MCP `codebase-memory` y repo indexado.

## Uso

`/impacto [rango git]`

## Metodo

1. Llama `mcp_codebase_memory_detect_changes` con el rango git o sin argumentos.
2. Presenta: simbolos tocados y su superficie de impacto (quienes dependen de ellos).
