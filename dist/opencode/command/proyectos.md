---
description: "Lista los proyectos indexados en codebase-memory y su estado (envuelve list_projects)."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/commands/proyectos.md (cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->

# /proyectos

Argumentos: `$ARGUMENTS` -- (sin argumentos)

## Instrucciones

Listá los **proyectos indexados** en el grafo de codebase-memory.

- Llamá `list_projects`.
- Presentá en español: nombre de cada proyecto y, si está disponible, su estado/tamaño
  (nodos/aristas) y cuándo se indexó.
- Si está vacío, sugerí correr `/indexar` en el repo que quieras.

## NOTA (OpenCode / MCP)

Este comando envuelve tools del MCP `codebase-memory`. En OpenCode se exponen con el prefijo del server (p. ej. `codebase-memory-mcp_search_graph` si el server se llama `codebase-memory-mcp` en `opencode.json`). Si el MCP no esta conectado, corre `/suite-setup` primero.
