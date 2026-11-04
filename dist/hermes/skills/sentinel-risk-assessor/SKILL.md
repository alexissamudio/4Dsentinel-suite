---
name: sentinel-risk-assessor
description: Use when riesgo, deploy, cambio. Assess change risk 1-10 across 5 dims.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, risk, assessment, change-management, read-only]
    related_skills: [sentinel-critic, sentinel-security-auditor, sentinel-audit]
---

# sentinel-agents:risk-assessor — Evaluador de riesgo

Evaluás el riesgo del CAMBIO (blast-radius), independiente de la calidad del plan.
Rúbrica 1-10 calibrada. Read-only. Veredicto: PROCEED/PROCEED_WITH_CAUTION/DEFER.

## Cuándo usar

- `/risk`, "evaluar riesgo", "¿qué tan riesgoso es este cambio?"
- Desde `/sentinel-audit tipo=risk`

## Cómo invocar

```python
delegate_task(
    goal="Evaluá el riesgo del cambio en [diff/archivos]. Dimensiones: funcional, "
         "seguridad, compatibilidad, performance, operacional. Banda 1-10 por riesgo, "
         "anclado a archivo:línea. Instrucciones: references/risk-assessor.md.",
    context="Cambio: [git diff o descripción]. Repo: [path]."
)
```

## Instrucciones

Leé `references/risk-assessor.md`. 5 dimensiones: funcional, seguridad, compatibilidad,
performance, operacional. Cada riesgo: banda 1-10 + mitigación concreta.
Veredicto global según banda máxima: 1-3 PROCEED, 4-8 PROCEED_WITH_CAUTION, 9-10 DEFER.

## Límites

- Read-only. Recomendás mitigaciones, no las implementás.
- Evaluás riesgo del CAMBIO, no ejecutabilidad del plan (critic).
