---
description: "Indexa un repositorio en el grafo de codebase-memory (envuelve index_repository). Deja el artefacto dentro del repo."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/commands/indexar.md. NO editar a mano. -->

# /indexar

Wrapper del comando de memoria `indexar`. El cuerpo canonico vive en el fuente de la suite (plugins/memory/commands/indexar.md).

Argumentos: `$ARGUMENTS` — [ruta del repo; por defecto el directorio actual]

## Instrucciones

Indexá el repositorio en el grafo de **codebase-memory**.

- **Ruta:** si `$ARGUMENTS` trae una ruta, usala; si no, usá el directorio de trabajo actual.
- Llamá la tool `index_repository` del MCP codebase-memory con `repo_path=<ruta>`,
  `mode="moderate"` y **`persistence=true`** (así el artefacto `.codebase-memory/graph.db.zst`
  queda **dentro del repo**, no esparcido en la caché global).
- Al terminar, resumí en español: nodos, aristas, lenguajes detectados, y confirmá que el
  artefacto quedó escrito en el repo.


## NOTA (OpenCode / MCP)

Este comando envuelve herramientas del MCP `codebase-memory`. Si el MCP no esta conectado, corre `/suite-setup` primero.
