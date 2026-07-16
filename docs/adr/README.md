# Architecture Decision Records (ADR)

Las **decisiones de arquitectura** de este repo viven acá, como archivos Markdown
**versionados en git** — la fuente de verdad. Cada ADR captura una decisión no obvia:
el contexto, la opción elegida y sus consecuencias.

## Por qué archivos fuente (F19 de la auditoría 2026-07-15)

El grafo de `codebase-memory` (`.codebase-memory/graph.db.zst`) es un **caché
reconstruible**: lo regenera `index_repository` a partir del código. Una decisión que
viva **solo** en el grafo se pierde al re-indexar. Por eso los ADR son archivos fuente
versionados; el grafo puede ingerirlos, pero no es su hogar.

## Convención

- Un archivo por decisión: `NNNN-titulo-en-kebab-case.md` (numeración incremental de 4
  dígitos, empezando en `0001`).
- Formato **MADR** liviano (ver [`0000-template.md`](0000-template.md)).
- Estados: `proposed` → `accepted` → (`deprecated` | `superseded por NNNN`). Un ADR
  aceptado **no se edita** salvo su estado; una decisión nueva que lo reemplace es un
  ADR nuevo que lo marca como `superseded`.
- Escribí un ADR cuando la decisión sea **costosa de revertir** o **no obvia** para
  alguien que lea solo el código (elección de tooling, un trade-off con alternativas
  reales, una restricción estructural).

## Índice

| # | Título | Estado |
|---|--------|--------|
| [0001](0001-mutmut-pineado-2x.md) | mutmut pineado a 2.x para mutar los hooks-subprocess | accepted |
