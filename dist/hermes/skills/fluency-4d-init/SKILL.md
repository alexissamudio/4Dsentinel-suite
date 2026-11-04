---
name: fluency-4d-init
description: Use when documentar, puentes, onboarding. Build .hermes.md with doc bridges.
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, 4d, hermes-md, puentes, documentation]
    related_skills: [fluency-4d, fluency-4d-status]
---

# /4d-init — Generador de documentación modular con puentes por tema

Convertí la documentación del proyecto en **disclosure progresivo por TEMA**: un
`.hermes.md` raíz corto con una tabla de puentes, y un doc por tema en `.hermes/docs/`.

Aplicá las 4D al propio proceso: vos explorás y redactás (Delegación), el usuario
decide los temas y aprueba antes de escribir (Discernimiento humano).

## Fase 1 — Descubrimiento

1. Leé el `.hermes.md` raíz si existe (contenido a PRESERVAR, nunca pisar).
   Si no existe, buscá `CLAUDE.md` o `AGENTS.md` para aprovechar contenido.
2. Si ya existe `.hermes/docs/bridges.json`, entrás en **modo actualización**.

## Fase 2 — Exploración (Delegación)

Lanzá `delegate_task` EN PARALELO para detectar los temas reales del proyecto.
Candidatos típicos: autenticación, endpoints/API, base de datos/modelos, deploy/CI,
testing, configuración, arquitectura general. **Solo proponé temas con evidencia
concreta en el código** — nada especulativo.

## Fase 3 — Confirmación con el usuario

Presentá los temas detectados con su evidencia y usá `clarify` (multiSelect)
para que el usuario elija cuáles generar.

## Fase 4 — Generación

Por cada tema aprobado, generá `.hermes/docs/<tema>.md` (30–80 líneas) con:
```yaml
---
generated: <fecha ISO>
source: fluency-4d-init
---
```
El contenido: cómo funciona el tema EN ESTE proyecto (archivos clave, flujo,
convenciones, gotchas) — no teoría genérica.

`.hermes/docs/convenciones.md` se genera SIEMPRE. Generá `.hermes/docs/bridges.json`:
```json
{ "version": 1, "temas": [
    { "tema": "auth", "archivo": ".hermes/docs/auth.md",
      "keywords": ["auth", "autenticacion", "login", "token", "sesion", "jwt"],
      "rutas": ["src/auth/", "config/auth.js"] }
] }
```
Keywords: específicas, español sin acentos + inglés, ≥3 chars. Rechazá genéricas.

## Fase 4.5 — Reglas-siempre vs conocimiento-por-tema

**Regla-siempre**: imperativa + un revisor la marcaría en cualquier diff → inline en `.hermes.md`.
**Conocimiento-por-tema**: cómo funciona X acá → `.hermes/docs/<tema>.md`. Ante la duda: inline.
Confirmá con `clarify` multiSelect; no clasifiques en silencio.

## Fase 5 — Fusión en .hermes.md

1. Mostrá resumen al usuario y esperá aprobación.
2. Backup: `.hermes/backups/.hermes.md.<fecha>.bak`.
3. Insertá SOLO entre centinelas:
```markdown
<!-- BEGIN 4D-BRIDGES -->
## Reglas del proyecto (siempre)
- ...

## Puentes de documentación
| Tema | Cuándo leer | Archivo |
|------|-------------|---------|

Si la pregunta toca un tema de la tabla, LEÉ ese archivo ANTES de responder.
Al escribir código, respetá `.hermes/docs/convenciones.md`.
<!-- END 4D-BRIDGES -->
```

## Re-ejecución

- Docs existentes: preguntar antes de regenerar.
- Temas nuevos: proponer. Obsoletos: proponer eliminar.
- Bloque entre centinelas se regenera; resto intacto.

## Reglas duras

- NUNCA tocar fuera de centinelas. NUNCA crear docs sin evidencia.
- SIEMPRE backup antes de modificar.
- Cerrá: "Docs generados con IA; revisalos antes de confiar."

## Nota Hermes

Portado de Claude Code. Paths: `.hermes/` en vez de `.claude/`. Sin hooks automáticos.
