---
name: memory-arquitectura
description: Use when arquitectura, mapa, estructura. Show project architecture graph via MCP.
version: 0.6.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [memory, codebase-memory, mcp, architecture, graph]
    related_skills: [memory-indexar, memory-buscar]
---

# /arquitectura — Mapa de arquitectura (MCP codebase-memory)

Muestra el mapa de arquitectura del grafo: stack, rutas, hotspots y clusters.

**Requiere:** MCP `codebase-memory` y repo indexado.

## Uso

`/arquitectura [proyecto]`

## Metodo

1. Resolve el proyecto via `mcp_codebase_memory_list_projects`.
2. Llama `mcp_codebase_memory_get_architecture` con `aspects=["overview"]`.
3. Presenta: stack, paquetes, rutas API, hotspots (top 3-5 por fan-in), clusters.
