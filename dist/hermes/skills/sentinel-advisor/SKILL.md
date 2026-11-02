---
name: sentinel-advisor
description: Use when planificar, requisitos, gap. Pre-plan gap analysis vs real code.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, advisor, pre-plan, gap-analysis, read-only]
    related_skills: [fluency-4d, sentinel-critic, sentinel-audit]
---

# sentinel-agents:advisor — Análisis pre-plan

Encontrás lo que va a hacer fallar un plan ANTES de que se escriba: requisitos
ocultos, supuestos no dichos, casos borde, riesgo de alcance y sobre-ingeniería.

## Cuándo usar

- Antes de escribir un plan de implementación
- Cuando el usuario dice `/advisor`, "gap analysis", "analizar requisitos"
- Automáticamente desde `/4d` Fase 1

## Cómo invocar

Usá `delegate_task` con el goal describiendo la tarea y el contexto del repo.
El subagente debe recibir acceso al código (Read/Grep/Glob) y seguir las
instrucciones de `references/advisor.md`.

```python
delegate_task(
    goal="Hacé un gap analysis pre-plan de: [descripción de la tarea]. "
         "Leé el código relevante y reportá requisitos ocultos, supuestos, "
         "casos borde y riesgo de alcance. "
         "Seguí las instrucciones en references/advisor.md.",
    context="Repositorio: [path]. Rama: [rama]. Tarea: [descripción]. "
            "Criterio de éxito: [criterio]."
)
```

## Instrucciones del agente

Leé `references/advisor.md` para las instrucciones completas. En resumen:
- PROHIBIDO afirmar sin leer el código: citá `archivo:línea`
- Sondeá TODAS las clases de gap (dependencias, criterios, bordes, seguridad, tests, etc.)
- Cada gap: por qué importa + evidencia + qué pasa si se ignora + acción de cierre
- Severidad: Critical/Important/Minor
- Salida: bloque `=== SENTINEL-REPORT ===` con `agent: advisor`, verdict, findings

## Límites

- Read-only. NO escribís el plan — lo analizás.
- Operás ANTES del plan. Un plan YA escrito lo revisa `sentinel-critic`.
