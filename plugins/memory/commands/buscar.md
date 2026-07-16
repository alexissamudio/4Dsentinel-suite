---
description: Busca funciones, clases y rutas en el grafo de codigo (envuelve search_graph), en vez de grep.
argument-hint: "<consulta en lenguaje natural o patron, ej. 'login de usuarios'>"
allowed-tools: ["mcp__codebase-memory__search_graph", "mcp__codebase-memory__list_projects"]
---

Buscá en el **grafo de código** del proyecto indexado (en vez de grep).

- **Proyecto:** resolvelo del repo actual (`list_projects` + directorio de trabajo) si el usuario
  no lo da.
- Llamá `search_graph` con `query="$ARGUMENTS"` (búsqueda BM25 en lenguaje natural). Si el usuario
  pasa un patrón regex explícito, usá `name_pattern` en su lugar.
- Presentá en español: nombre, tipo (función/clase/ruta), archivo, y grado (conexiones) si aporta.
  Si la respuesta trae `has_more=true`, avisá que hay más y ofrecé paginar.
