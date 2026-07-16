---
description: Muestra el mapa de arquitectura de un proyecto indexado (envuelve get_architecture): stack, rutas, hotspots y clusters.
argument-hint: "[nombre del proyecto; por defecto el del repo actual]"
allowed-tools: ["mcp__codebase-memory__get_architecture", "mcp__codebase-memory__list_projects"]
---

Mostrá el **mapa de arquitectura** de un proyecto indexado.

- **Proyecto:** si `$ARGUMENTS` lo especifica, usalo. Si no, resolvé el proyecto del repo actual
  (llamá `list_projects` y matcheá por el directorio de trabajo); si hay ambigüedad, preguntá.
- Llamá `get_architecture` con `aspects=["overview"]` (o `["all"]` si el usuario pide más detalle).
- Presentá en español: stack/lenguajes, paquetes, rutas (API), entry points, **hotspots**
  (funciones más llamadas, por fan-in) y **clusters** (los módulos reales del grafo). Destacá los
  3-5 hotspots principales.
