---
generated: 2026-07-03
source: 4d-init
content_hash: a0a46d8c9ca10cda16db9b0b88d9003858f7f02e1e776d01a9fb10017b1134b3
---

# Skills en este proyecto

Cinco skills en `plugins/fluency-4d/skills/<nombre>/SKILL.md`: `4d` (flujo
guiado por las 4 dimensiones), `4d-init` (generador de puentes), `4d-status`
(reporte de solo lectura), `4d-quiz` (práctica de certificación) y `caveman`
(toggle de estilo token-eficiente).

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

## Contrato (reglas duras validadas por check_skills.py)

`uv run scripts/check_skills.py` es el validador determinístico del contrato (corre
en CI). Es convención PROPIA de fluency-4d, no la plantilla ajena de otros plugins:
acá el cuerpo NO tiene que "referenciar el contrato", y NO se exige sección `##
Reglas` ni un límite de líneas duro (el límite de 150 es guía, a lo sumo warning).

### Arquetipos propios

Toda skill cae en uno de tres arquetipos (define el estilo, no cambia las reglas
universales — todas las cumplen por igual):

- **Workflow guiado** (`/4d`, `/4d-init`): flujo multifase que INSTRUYE a Claude
  paso a paso; suele traer `references/*.md` con contenido pedagógico cargado bajo
  demanda. Triggers: literal + frases naturales.
- **Comando-tool** (`/4d-status`, `/4d-quiz`): invocación puntual y acotada (reporte
  read-only o utilidad). Triggers SOLO literales para no auto-dispararse.
- **Toggle** (`/caveman`): prende/apaga un flag global; el trabajo real lo hace un
  hook. Opt-in, arranca apagado.

### Reglas universales (las cumplen las 5 skills)

1. **`name` == directorio.** El frontmatter lleva `name` y es idéntico al nombre de
   la carpeta de la skill.
2. **`description` con activación.** Hay `description` y contiene la subcadena
   `Triggers on:` (las frases que disparan la skill).
3. **H1 presente.** El cuerpo abre con un título `# ...` (convención: `# /nombre — …`).
4. **Registro DOBLE sin huérfanos.** Cada skill en `skills/` está listada en AMBOS
   `plugin.json` (`skills[]`) y `marketplace.json` (`plugins[0].skills[]`), y ninguno
   de los dos lista skills que no existan en disco (ver "Regla del registro DOBLE").
5. **Refs no huérfanas.** Toda `references/<x>.md` citada en un SKILL.md existe.
6. **Auto-contención.** Ningún path de máquina (`C:\Users\`, `/home/`, `/Users/`) en
   los `.md`/`.py` del plugin.
