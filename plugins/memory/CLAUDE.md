# codebase-memory

Grafo de código del repo (funciones, clases, rutas, llamadas) vía el MCP
`codebase-memory`. Deja el artefacto `.codebase-memory/` dentro del repo. Comandos:
`/indexar`, `/arquitectura`, `/buscar`, `/rastrear`, `/impacto`, `/proyectos`.

## Cuándo ofrecer el grafo

Ofrecé (no indexes ni consultes por tu cuenta cuando implica escribir); el humano confirma:

- **Repo grande o "entender / mapear / explorar / onboarding" de este repo** →
  ofrecé indexarlo con `/indexar` y recorrer la arquitectura con `/arquitectura`.
- **"¿quién llama a X?" / "¿qué impacto tiene este cambio?"** → ofrecé `/rastrear`
  o `/impacto` (consultar el grafo) en vez de grep a mano.

Dos aclaraciones operativas:

- Los agentes de plugin (sentinel-agents, subagentes) **NO ven el MCP**: el
  conductor consulta el grafo (`search_graph`/`trace_path`/`get_architecture`)
  UNA vez y **relaya un brief conciso** al resto. Esto AHORRA TOKENS: sin el
  brief, cada agente re-explora los mismos archivos a mano (fan-out caro); con
  el brief, trabajan sobre el resultado del grafo. Consultá una vez, relayá a
  todos.
- Indexar **escribe `.codebase-memory/` en el repo** (toca el disco del usuario):
  **ofrecé, no indexes sin confirmar.** Declinar no debe tener fricción.
