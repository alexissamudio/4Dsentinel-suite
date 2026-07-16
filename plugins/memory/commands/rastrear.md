---
description: Rastrea llamadores/llamados e impacto de una funcion en el grafo (envuelve trace_path).
argument-hint: "<nombre de la funcion> [inbound|outbound|both]"
allowed-tools: ["mcp__codebase-memory__trace_path", "mcp__codebase-memory__list_projects"]
---

Rastreá el **grafo de llamadas** de una función (análisis de impacto).

- **Proyecto:** resolvelo del repo actual si no se da.
- De `$ARGUMENTS`: el primer token es la función; si incluye `inbound`/`outbound`/`both`, usalo
  como `direction` (por defecto **`inbound`** = quién la llama = superficie de impacto).
- Llamá `trace_path` con `function_name=<función>`, `direction=<dir>`, `depth=2`.
- Presentá en español: llamadores/llamados agrupados por archivo/componente, y una lectura del
  **impacto** (dónde repercutiría un cambio a esa función).
