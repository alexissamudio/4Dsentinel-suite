---
description: "Lista los proyectos indexados en codebase-memory y su estado (envuelve list_projects)."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/commands/proyectos.md. NO editar a mano. -->

# /proyectos

Wrapper del comando de memoria `proyectos`. El cuerpo canonico vive en el fuente de la suite (plugins/memory/commands/proyectos.md).

Argumentos: `$ARGUMENTS` — (sin argumentos)

## Instrucciones

Listá los **proyectos indexados** en el grafo de codebase-memory.

- Llamá `list_projects`.
- Presentá en español: nombre de cada proyecto y, si está disponible, su estado/tamaño
  (nodos/aristas) y cuándo se indexó.
- Si está vacío, sugerí correr `/indexar` en el repo que quieras.


## NOTA (OpenCode / MCP)

Este comando envuelve herramientas del MCP `codebase-memory`. Si el MCP no esta conectado, corre `/suite-setup` primero.
