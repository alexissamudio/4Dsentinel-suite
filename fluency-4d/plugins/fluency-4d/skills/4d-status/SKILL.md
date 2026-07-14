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
4b. **Sección de reglas** — leé el bloque centinela del `CLAUDE.md`: reportá si
   existe "## Reglas del proyecto (siempre)" y cuántas reglas tiene. Si el bloque
   NO la tiene (proyecto inicializado con v0.4), sugerí "re-ejecutá /4d-init para
   separar las reglas-siempre de los puentes: hoy tus reglas no negociables podrían
   estar solo en convenciones.md, gated por keyword".
5. **Métricas de uso** — leé `~/.claude/fluency4d/stats.json` y buscá la
   entrada cuya clave es la ruta resuelta de este proyecto en minúsculas
   (`str(Path(cwd).resolve()).casefold()`). Reportá: sesiones registradas y,
   por tema, las inyecciones. **Puentes con 0 inyecciones en varias sesiones
   → candidatos a podar.** Si no hay entrada: "sin datos de uso todavía".
   (Los contadores son best-effort: señal, no contabilidad.)
6. **Staleness de docs** — por cada tema con `rutas`, compará la fecha de
   commit del doc contra la del código:
   `git log -1 --format=%ct -- <archivo-doc>` vs el máximo de
   `git log -1 --format=%ct -- <ruta>` entre sus rutas. Si el código es más
   nuevo → "el doc quedó detrás de cambios en <ruta>". Sumá
   `git status --porcelain -- <ruta>` para detectar cambios sin commitear.
   Si el proyecto NO es un repo git: fallback a mtime CON el disclaimer de
   que clones/checkouts lo hacen impreciso. NO uses mtime en repos git
   (checkout resetea mtimes → falsos positivos).

## Formato del reporte

Tabla corta de temas + tres líneas de estado (lecciones, sesión, convenciones)
+ una sección "Sugerencias" SOLO con acciones que apliquen (no listar las que
no). Cerrá en menos de 25 líneas.
