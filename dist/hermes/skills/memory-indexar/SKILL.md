---
name: memory-indexar
description: Use when indexar, index. Index repo into codebase-memory graph via MCP.
version: 0.6.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [memory, codebase-memory, mcp, index, graph]
    related_skills: [memory-buscar, memory-proyectos]
---

# /indexar — Indexar repositorio (MCP codebase-memory)

Indexa un repositorio en el grafo de codebase-memory. El artefacto queda dentro del repo.

**Requiere:** MCP `codebase-memory` configurado y `codebase-memory-mcp` instalado.

## Uso

`/indexar [ruta del repo]`

## Metodo

1. Si no se especifica ruta, usa el directorio actual.
2. Llama `mcp_codebase_memory_index_repository` con `repo_path=<ruta>`, `mode="moderate"`, `persistence=true`.
3. Resume: nodos, aristas, lenguajes detectados. El artefacto queda en el repo.
