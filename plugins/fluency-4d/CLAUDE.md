# fluency-4d

Este plugin aplica el marco **4D de AI Fluency** (Delegación, Descripción, Discernimiento, Diligencia).

- Para tareas grandes o ambiguas, ofrecé usar `/4d` (flujo guiado por las 4 dimensiones).
- Si el proyecto no tiene CLAUDE.md modular, ofrecé `/4d-init` (genera CLAUDE.md con tabla de puentes + docs por tema en `.claude/docs/`).
- Si el CLAUDE.md del proyecto tiene una tabla de "Puentes de documentación", LEÉ el archivo del tema correspondiente ANTES de responder preguntas sobre ese tema.
- Cuando el usuario te corrija algo no trivial, ofrecé guardar la lección en `.claude/docs/lecciones.md` (formato `## [fecha] — [título]` + contexto + lección + cómo aplicar; máx ~30, consolidá duplicadas).
- Cuando recibas la instrucción del checkpoint de memoria (fluency-4d, ~50% de contexto), escribí `.claude/docs/estado-sesion.md` con encabezado de fecha, objetivo/frase 4D, decisiones tomadas y pendientes, y seguí con la tarea.
