---
description: "Busca funciones, clases y rutas en el grafo de codigo (envuelve search_graph), en vez de grep."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/commands/buscar.md (cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->

# /buscar

Argumentos (`$ARGUMENTS`): <consulta en lenguaje natural o patron, ej. 'login de usuarios'>

## Instrucciones

Buscá en el **grafo de código** del proyecto indexado (en vez de grep).

- **Proyecto:** resolvelo del repo actual (`list_projects` + directorio de trabajo) si el usuario
  no lo da.
- Llamá `search_graph` con `query="$ARGUMENTS"` (búsqueda BM25 en lenguaje natural). Si el usuario
  pasa un patrón regex explícito, usá `name_pattern` en su lugar.
- Presentá en español: nombre, tipo (función/clase/ruta), archivo, y grado (conexiones) si aporta.
  Si la respuesta trae `has_more=true`, avisá que hay más y ofrecé paginar.

## NOTA (OpenCode / MCP)

Este comando envuelve tools del MCP `codebase-memory`. En OpenCode se exponen con el prefijo del server (p. ej. `codebase-memory-mcp_search_graph` si el server se llama `codebase-memory-mcp` en `opencode.json`). Si el MCP no esta conectado, corre `/suite-setup` primero.
