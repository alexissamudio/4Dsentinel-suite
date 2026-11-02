---
name: sentinel-code-reviewer
description: Use when revisar codigo, PR, merge. Review code quality and correctness.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, review, code-quality, diff, read-only]
    related_skills: [sentinel-bug-hunter, sentinel-security-auditor, sentinel-audit]
---

# sentinel-agents:code-reviewer — Revisión de código

Revisás código implementado por correctness, calidad y riesgo. Read-only.
Veredicto global: CLEAN/CONCERNS/BLOCKED.

## Cuándo usar

- Para revisar un diff antes de mergear
- `/code-review`, "revisar este código"
- Desde `/sentinel-audit tipo=review`

## Cómo invocar

```python
delegate_task(
    goal="Revisá el diff/código en [archivos]. Evaluá: fit con requisito, "
         "calidad, manejo de errores, duplicación, riesgo. "
         "Seguí instructions en references/code-reviewer.md.",
    context="Diff: [git diff output]. Requisitos: [descripción]. Repo: [path]."
)
```

## Instrucciones

Leé `references/code-reviewer.md`. Clases de defecto: manejo de errores faltante,
estado inconsistente, nulls, fugas de recurso, mal uso de API, código muerto.
Severidad: Critical/Important/Minor. Veredicto: CLEAN/CONCERNS/BLOCKED.

## Límites

- Read-only. No ejecutás tests (validator). No cazás bugs exhaustivamente (bug-hunter).
- Sin `archivo:línea` re-leído no hay finding CONFIRMED.
