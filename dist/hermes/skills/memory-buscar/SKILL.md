---
name: memory-buscar
description: Use when buscar, search, consulta. Search codebase graph via MCP.
version: 0.6.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [memory, codebase-memory, mcp, search, graph]
    related_skills: [memory-indexar, memory-arquitectura]
---

# /buscar — Buscar en el grafo de codigo (MCP codebase-memory)

Busca en el **grafo de codigo** del proyecto indexado (busqueda semantica BM25), en vez de grep.

**Requiere:** MCP `codebase-memory` y repo indexado (`/indexar`).

## Uso

`/buscar <consulta en lenguaje natural>`

## Metodo

1. Resolve el proyecto: `mcp_codebase_memory_list_projects` y matchea.
2. Llama `mcp_codebase_memory_search_graph` con `query="<consulta>"`.
3. Presenta: nombre, tipo (funcion/clase/ruta), archivo, grado (conexiones). Si `has_more=true`, ofrece paginar.
