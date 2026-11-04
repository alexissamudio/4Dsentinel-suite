---
name: fluency-adhd
description: Use when adhd, tdah, foco, accionable. Toggle structured actionable output style.
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, adhd, focus, actionable, communication]
    related_skills: [fluency-caveman]
---

# /adhd — Toggle del modo de comunicación accionable y estructurada

Este skill activa/desactiva el modo ADHD EN LA SESIÓN ACTUAL.
El modo ADHD arranca **APAGADO**.

## 1. Parseá el argumento

- `auto`, `lite`, `full` → ON en ese nivel.
- `/adhd` pelado → `auto`.
- `off` → apagar.

## 2. Aplicá el estilo

**Invariante (todos los niveles):** no elimines pasos, advertencias ni detalles que
cambien la correctitud. Código, comandos, rutas, IDs, errores y URLs = byte-por-byte.
Las reglas se relajan en explicaciones, confirmación de acción destructiva, ambigüedad
real o espiral de debugging. Conserva el idioma del usuario.

**Nivel AUTO**: en tareas multi-paso aplica FULL; en consultas cortas aplica LITE.

**FULL**: pasos numerados, restate-state, next-step concreto, estimaciones.
**LITE**: reglas siempre-seguras, sin restate-state ni estimaciones.

Si activás ADHD, apagá caveman (mutuamente excluyentes).

## 3. Confirmá

- ON: confirmá YA en estilo ADHD (arrancá por la acción, sin preámbulo).
- OFF: confirmá en estilo normal.

## Nota Hermes

En Claude Code este skill escribe `~/.claude/fluency4d/adhd.json` y el hook inyecta.
En Hermes, aplicás el estilo directamente en tus respuestas durante la sesión.
