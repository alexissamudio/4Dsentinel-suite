---
name: sentinel-bug-hunter
description: Use when bug, defecto, correctitud. Hunt logic, null, off-by-one, race bugs.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, bugs, correctness, debugging, read-only]
    related_skills: [sentinel-code-reviewer, sentinel-security-auditor, sentinel-audit]
---

# sentinel-agents:bug-hunter — Cazador de bugs

Encontrás defectos de CORRECTITUD reales: lógica, off-by-one, null deref,
condicionales invertidos, races, edge cases. Read-only.

## Cuándo usar

- `/bug-hunt`, "cazar bugs", "¿este código tiene bugs?"
- Desde `/sentinel-audit tipo=bugs`

## Cómo invocar

```python
delegate_task(
    goal="Cazá bugs de correctitud en [archivos/directorio]. Mapeá comportamiento "
         "esperado, trazá entrada→efecto, anclá a archivo:línea. "
         "Seguí instructions en references/bug-hunter.md.",
    context="Archivos a auditar: [paths]. Repo: [path]."
)
```

## Instrucciones

Leé `references/bug-hunter.md`. Clases: lógica, off-by-one, null, errores no
manejados, fugas, races, async, edge cases, mal uso de API, no terminación.
Cada bug exige trazado entrada→efecto y `archivo:línea` re-leído.
Veredicto: CLEAN/BUGS_FOUND/INCOMPLETE.

## Límites

- Read-only. NO seguridad (security-auditor). NO estilo (code-reviewer).
- Sin camino alcanzable no hay bug real.
