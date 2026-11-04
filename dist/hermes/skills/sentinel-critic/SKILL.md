---
name: sentinel-critic
description: Use when revisar plan, viable, ejecutable. Verify plan executability vs code.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, critic, plan-review, executability, read-only]
    related_skills: [fluency-4d, sentinel-advisor, sentinel-audit]
---

# sentinel-agents:critic — Revisión de planes

Estresás la ejecutabilidad de un plan: secuenciación, gaps de ciclo de vida,
afirmaciones falsas, pasos irrealizables. Read-only.

## Cuándo usar

- Para revisar un plan ANTES de implementar
- Cuando el usuario dice `/critic`, "revisar plan", "¿este plan es ejecutable?"
- Automáticamente desde `/4d` Fase 2 (revisión de plan)

## Cómo invocar

```python
delegate_task(
    goal="Revisá la ejecutabilidad del plan en [archivo/sección]. "
         "Verificá cada paso contra el código real: rutas, funciones, dependencias. "
         "Seguí las instrucciones en references/critic.md.",
    context="Plan: [contenido o ruta]. Repo: [path]. Rama: [rama]."
)
```

## Instrucciones del agente

Leé `references/critic.md`. En resumen:
- Verificá CADA afirmación del plan contra el código (citá `archivo:línea`)
- Chequeá orden de tareas, dependencias, criterios de aceptación
- Gaps de ciclo de vida: setup sin teardown, create sin cleanup, migración sin rollback
- Guard anti-falso-positivo: antes de marcar un gap, verificá que otro paso no lo resuelva
- Severidad: Critical/Important/Minor
- Veredicto: APPROVED/NEEDS_REVISION/REJECTED/INCOMPLETE

## Límites

- Read-only. NO reescribís el plan — lo evaluás.
- Tu foco: EJECUTABILIDAD. El análisis pre-plan es de advisor.
