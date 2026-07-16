---
description: Indexa un repositorio en el grafo de codebase-memory (envuelve index_repository). Deja el artefacto dentro del repo.
argument-hint: "[ruta del repo; por defecto el directorio actual]"
allowed-tools: ["mcp__codebase-memory__index_repository"]
---

Indexá el repositorio en el grafo de **codebase-memory**.

- **Ruta:** si `$ARGUMENTS` trae una ruta, usala; si no, usá el directorio de trabajo actual.
- Llamá la tool `index_repository` del MCP codebase-memory con `repo_path=<ruta>`,
  `mode="moderate"` y **`persistence=true`** (así el artefacto `.codebase-memory/graph.db.zst`
  queda **dentro del repo**, no esparcido en la caché global).
- Al terminar, resumí en español: nodos, aristas, lenguajes detectados, y confirmá que el
  artefacto quedó escrito en el repo.
