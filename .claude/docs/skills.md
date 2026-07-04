---
generated: 2026-07-03
source: 4d-init
content_hash: a0a46d8c9ca10cda16db9b0b88d9003858f7f02e1e776d01a9fb10017b1134b3
---

# Skills en este proyecto

Cuatro skills en `plugins/fluency-4d/skills/<nombre>/SKILL.md`: `4d` (flujo
guiado por las 4 dimensiones), `4d-init` (generador de puentes), `4d-status`
(reporte de solo lectura) y `4d-quiz` (práctica de certificación).

## Anatomía

- Frontmatter mínimo: `name` + `description`. La description lleva las frases
  de activación: `Triggers on: '/nombre', 'frase alternativa'`.
- Contenido pedagógico o banco de datos va en `references/*.md` dentro de la
  skill (disclosure progresivo: se carga bajo demanda, no infla el SKILL.md).
  Ej.: `4d/references/{delegacion,descripcion,discernimiento,diligencia}.md`
  y `4d-quiz/references/preguntas.md` (24 preguntas × 5 partes).
- Límite práctico: SKILL.md < 150 líneas; si crece, mover contenido a references.

## Regla del registro DOBLE (la que siempre se olvida)

Las skills NO se auto-descubren. Cada skill nueva se lista en DOS lugares:

1. `plugins/fluency-4d/.claude-plugin/plugin.json` → `"skills": ["./skills/<nombre>"]`
2. `.claude-plugin/marketplace.json` → `plugins[0].skills` (espejo del anterior)

Se apunta al DIRECTORIO de la skill, no al SKILL.md. Olvidar el segundo lugar
hace que la skill funcione localmente y desaparezca al instalar desde el
marketplace.

## Convenciones propias

- Todo en español (voseo rioplatense), siguiendo el PDF de AI Fluency.
- `/4d-status` y `/4d-quiz` usan triggers SOLO literales para no auto-dispararse.
- Las skills instruyen, no ejecutan código: la generación (4d-init) la hace
  Claude siguiendo las fases; los hooks solo enrutan.
- Reglas duras al final de cada SKILL.md (sección "Reglas"): son el contrato.
