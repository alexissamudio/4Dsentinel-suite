---
name: 4d-init
description: "Genera un CLAUDE.md modular con 'puentes' a documentación por tema: analiza el proyecto, crea .claude/docs/<tema>.md (auth, endpoints, database...) más bridges.json, y enlaza todo desde una tabla en CLAUDE.md sin pisar el contenido existente. Triggers on: '/4d-init', 'generar puentes', 'claude.md modular', 'puentes de documentacion'."
---

# /4d-init — Generador de CLAUDE.md con puentes por tema

Convertí la documentación del proyecto en **disclosure progresivo por TEMA**: un
CLAUDE.md raíz corto con una tabla de puentes, y un doc por tema en `.claude/docs/`.
El hook `bridge_router` del plugin usará `bridges.json` para que, cuando el usuario
pregunte por un tema, Claude lea el doc correspondiente ANTES de responder.

Aplicá las 4D al propio proceso: vos explorás y redactás (Delegación), el usuario
decide los temas y aprueba antes de escribir (Discernimiento humano).

## Fase 1 — Descubrimiento

1. Leé el `CLAUDE.md` raíz si existe (contenido a PRESERVAR, nunca pisar).
2. Buscá CLAUDE.md anidados (`**/CLAUDE.md` fuera de la raíz). Si hay (patrón
   init-deep), ADVERTÍ al usuario que van a convivir dos sistemas y pedí confirmación
   antes de seguir.
3. Si ya existe `.claude/docs/bridges.json`, entrás en **modo actualización** (ver
   "Re-ejecución" abajo).

## Fase 2 — Exploración (Delegación)

Lanzá agentes Explore EN PARALELO para detectar los temas reales del proyecto.
Candidatos típicos: autenticación, endpoints/API, base de datos/modelos, deploy/CI,
testing, configuración, arquitectura general. **Solo proponé temas con evidencia
concreta en el código** (archivos, rutas, dependencias) — nada especulativo.

## Fase 3 — Confirmación con el usuario

Presentá los temas detectados con su evidencia y usá AskUserQuestion (multiSelect)
para que el usuario elija cuáles generar. Proponé también las keywords por tema.

## Fase 4 — Generación

Por cada tema aprobado, generá `.claude/docs/<tema>.md` (30–80 líneas) con este
frontmatter obligatorio:

```yaml
---
generated: <fecha ISO>
source: 4d-init
content_hash: <sha256 del cuerpo, sin el frontmatter>
---
```

Calculá el hash con: `uv run python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <archivo-cuerpo>`
(o equivalente sobre el texto del cuerpo). El contenido: cómo funciona el tema EN ESTE
proyecto (archivos clave con rutas, flujo, convenciones, gotchas) — no teoría genérica.

**Excepción a la regla de evidencia:** `.claude/docs/convenciones.md` se genera
SIEMPRE (naming, formato, idioma de identificadores, estructura de carpetas,
linters detectados). Si la evidencia es poca, el doc lo dice honestamente:
línea "⚠ Generado con poca evidencia — validar" y `evidence: low` en el
frontmatter. Pasa por la misma protección de hash en re-ejecución. Su entrada
en bridges.json usa keywords específicas: `["convenciones", "styleguide",
"estilo de codigo", "lint", "linting", "naming"]` (NO "style"/"estilo"/"formato"
a secas: false-positives con estilos de UI).

Generá `.claude/docs/bridges.json`. Cada tema lleva **`rutas`**: prefijos de
ruta posix relativos a la raíz (carpetas con `/` final o archivos exactos),
derivados de la evidencia de la exploración — activan el aviso automático de
doc desactualizado cuando se editan archivos del tema:

```json
{ "version": 1, "temas": [
    { "tema": "auth", "archivo": ".claude/docs/auth.md",
      "keywords": ["auth", "autenticacion", "login", "token", "sesion", "jwt"],
      "rutas": ["src/auth/", "config/auth.js"] }
] }
```

**Reglas de keywords:** específicas del tema, en español (sin acentos: el hook
normaliza) e inglés; mínimo 4 caracteres; RECHAZÁ keywords genéricas que matchearían
en cualquier prompt ("api", "codigo", "test" solo, "base", "dato").

## Fase 4.5 — Reglas-siempre vs conocimiento-por-tema

Dos tipos de contenido: **conocimiento-por-tema** (cómo funciona X acá; solo
importa al tocar X) → `.claude/docs/<tema>.md` con puente. **Regla-siempre**
(aplica al escribir CUALQUIER código) → inline en el bloque centinela del
CLAUDE.md, que se carga en TODA sesión.

**Regla de decisión:** es **regla-siempre** sii (a) es imperativa/prohibitiva Y
(b) un revisor marcaría su violación en un diff SIN saber qué feature implementa.
**Ante la duda: inline** (falso positivo = 1 línea de ruido; falso negativo =
regla no negociable escondida tras un keyword). Ejemplos trabajados:
`references/ejemplo-clasificacion.md`.

**Confirmación humana:** generá los candidatos y presentálos con AskUserQuestion
multiSelect ("¿cuáles son no negociables e inline?"). NO clasifiques en silencio.
Apuntá a ≤10-12; más es decisión del usuario. El DETALLE (ejemplos bien/mal, el
porqué) va a `convenciones.md`; la línea inline lo restatea 1:1.

## Fase 5 — Fusión en CLAUDE.md (con Discernimiento)

1. **Mostrá al usuario un resumen** de todo lo que vas a escribir y esperá aprobación.
2. Si existe CLAUDE.md, copialo primero a `.claude/backups/CLAUDE.md.<fecha>.bak`.
3. Insertá o reemplazá SOLO el bloque entre centinelas — el resto del archivo no se toca:

Layout FIJO del bloque, en este orden: sección de reglas → tabla de puentes →
líneas de cierre:

```markdown
<!-- BEGIN 4D-BRIDGES -->
## Reglas del proyecto (siempre)
- SIEMPRE early returns; NUNCA if/else anidado.
- (una línea por regla-siempre confirmada, en el orden en que el usuario las eligió)

## Puentes de documentación
| Tema | Cuándo leer | Archivo |
|------|-------------|---------|
| Auth | login, tokens, sesiones | .claude/docs/auth.md |

Si la pregunta o tarea toca un tema de la tabla, LEÉ ese archivo ANTES de responder.
Al escribir código, respetá `.claude/docs/convenciones.md`.
<!-- END 4D-BRIDGES -->
```

- **Vacío-seguro:** sin reglas-siempre confirmadas, OMITÍ la sección
  "## Reglas del proyecto" entera (nada de `##` vacío). El pointer a
  `convenciones.md` SIEMPRE queda. Si no hay CLAUDE.md, crealo con título + bloque.
  Todo corto: una línea por regla y por tema; el detalle vive en los docs.

## Re-ejecución (modo actualización)

1. Por cada doc existente en `bridges.json`, recalculá el hash del cuerpo y comparalo
   con el `content_hash` del frontmatter.
2. **Si difieren, el humano lo editó: NO lo regeneres sin preguntar** (AskUserQuestion:
   conservar / regenerar / fusionar mostrando diferencias).
3. Temas nuevos detectados se proponen como en la Fase 3; temas cuyos archivos fuente
   desaparecieron se proponen para eliminar de la tabla.
4. El bloque entre centinelas se regenera; todo lo demás en CLAUDE.md queda intacto.
5. **Reglas-siempre (sin hash propio):** baseline = el backup previo. Compará la
   sección "## Reglas del proyecto" del bloque actual contra la del backup más
   reciente; si difieren, el humano las editó → AskUserQuestion (conservar /
   regenerar / fusionar). Orden de reglas estable entre corridas (evita diffs
   fantasma).

## Reglas duras

- NUNCA tocar contenido fuera de los centinelas `<!-- BEGIN 4D-BRIDGES -->` / `<!-- END 4D-BRIDGES -->`.
- `lecciones.md` y `estado-sesion.md` NO son docs de tema: no los regeneres ni los metas en `bridges.json` (los escribe Claude durante el trabajo, no este generador).
- NUNCA crear CLAUDE.md anidados por directorio (territorio de /init-deep); NUNCA generar un tema sin evidencia en el código.
- SIEMPRE backup antes de modificar un CLAUDE.md; NUNCA pisar el pointer "respetá convenciones.md" (la sección de reglas lo suplementa).
- Cerrá con nota de diligencia: "Docs generados con asistencia de IA (fluency-4d); revisalos antes de confiar en ellos."
