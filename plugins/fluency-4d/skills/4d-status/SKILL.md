---
name: 4d-status
description: "Muestra el estado del sistema fluency-4d en el proyecto actual: temas puenteados, lecciones, estado de sesión y sugerencias. Solo lectura. Triggers on: '/4d-status'."
---

# /4d-status — Estado del sistema de puentes y aprendizaje

Reporte de SOLO LECTURA sobre los archivos existentes del proyecto. NO lances
agentes, NO explores el código, NO escribas nada: leé estos archivos (los que
existan) y armá el reporte.

## Qué leer y qué reportar

1. **`.claude/docs/bridges.json`** — listá cada tema con sus keywords y archivo.
   - Marcá los **temas sin `rutas`**: "re-ejecutá `/4d-init` para activar el
     aviso de doc desactualizado en este tema".
   - Si no existe: "proyecto sin puentes — corré `/4d-init` para generarlos".
2. **`.claude/docs/lecciones.md`** — contá las lecciones (encabezados `## `).
   - Si se acercan a 30, sugerí consolidar (fusionar duplicadas, borrar
     supersedidas).
3. **`.claude/docs/estado-sesion.md`** — informá su edad (mtime). Si es de más
   de 24 h, sugerí revisarlo o borrarlo si la tarea ya terminó.
4. **`.claude/docs/convenciones.md`** — presente/ausente; si tiene
   `evidence: low` en el frontmatter, recordá validarlo.

## Formato del reporte

Tabla corta de temas + tres líneas de estado (lecciones, sesión, convenciones)
+ una sección "Sugerencias" SOLO con acciones que apliquen (no listar las que
no). Cerrá en menos de 25 líneas.
