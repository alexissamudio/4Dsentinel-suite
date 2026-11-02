---
name: memory-proyectos
description: Use when proyectos, listar. List indexed projects via MCP.
version: 0.6.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [memory, codebase-memory, mcp, projects, list]
    related_skills: [memory-indexar]
---

# /proyectos — Listar proyectos indexados (MCP codebase-memory)

Lista los proyectos en el grafo de codebase-memory.

**Requiere:** MCP `codebase-memory`.

## Uso

`/proyectos`

## Metodo

1. Llama `mcp_codebase_memory_list_projects`.
2. Presenta: nombre, estado, nodos/aristas, fecha de indexado.
3. Si vacio: sugiere `/indexar`.
