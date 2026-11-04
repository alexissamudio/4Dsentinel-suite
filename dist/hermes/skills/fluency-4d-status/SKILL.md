---
name: fluency-4d-status
description: Use when estado, diagnostico, status. Show project bridges, lessons, session.
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, 4d, status, diagnostics, read-only]
    related_skills: [fluency-4d, fluency-4d-init]
---

# /4d-status — Estado del sistema de puentes y aprendizaje

Reporte de SOLO LECTURA. NO lances agentes, NO explores código, NO escribas nada.

## Qué leer y reportar

1. **`.hermes/docs/bridges.json`** — listá cada tema con keywords y archivo.
   - Marcá temas sin `rutas`: "re-ejecutá /4d-init para activar aviso de doc desactualizado".
   - Si no existe: "proyecto sin puentes — corré /4d-init".
2. **Lecciones** — usá `memory` tool para consultar lecciones guardadas. Si hay muchas,
   sugerí consolidar.
3. **`.hermes/docs/estado-sesion.md`** — si existe, informá su edad (mtime). Si >24h,
   sugerí revisarlo o borrarlo.
4. **`.hermes/docs/convenciones.md`** — presente/ausente; si `evidence: low`, recordá validarlo.
5. **Sección de reglas** — leé `.hermes.md`: reportá bloque centinela y cuántas reglas tiene.
6. **Staleness de docs** — por cada tema con `rutas`, compará commit del doc vs código:
   `git log -1 --format=%ct -- <archivo-doc>` vs `git log -1 --format=%ct -- <ruta>`.
   Si código más nuevo → "doc detrás de cambios en <ruta>".

## Formato del reporte

Tabla corta de temas + líneas de estado + "Sugerencias" solo con acciones que apliquen.
Cerrá en menos de 25 líneas.

## Nota Hermes

Portado de Claude Code. Usa `.hermes/` en vez de `.claude/`. Las lecciones se consultan
con `memory` tool en vez de archivos.
