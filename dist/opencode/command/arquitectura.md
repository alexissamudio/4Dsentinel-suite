---
description: "Muestra el mapa de arquitectura de un proyecto indexado (envuelve get_architecture): stack, rutas, hotspots y clusters."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/commands/arquitectura.md. NO editar a mano. -->

# /arquitectura

Wrapper del comando de memoria `arquitectura`. El cuerpo canonico vive en el fuente de la suite (plugins/memory/commands/arquitectura.md).

Argumentos: `$ARGUMENTS` — [nombre del proyecto; por defecto el del repo actual]

## Instrucciones

Mostrá el **mapa de arquitectura** de un proyecto indexado.

- **Proyecto:** si `$ARGUMENTS` lo especifica, usalo. Si no, resolvé el proyecto del repo actual
  (llamá `list_projects` y matcheá por el directorio de trabajo); si hay ambigüedad, preguntá.
- Llamá `get_architecture` con `aspects=["overview"]` (o `["all"]` si el usuario pide más detalle).
- Presentá en español: stack/lenguajes, paquetes, rutas (API), entry points, **hotspots**
  (funciones más llamadas, por fan-in) y **clusters** (los módulos reales del grafo). Destacá los
  3-5 hotspots principales.


## NOTA (OpenCode / MCP)

Este comando envuelve herramientas del MCP `codebase-memory`. Si el MCP no esta conectado, corre `/suite-setup` primero.
